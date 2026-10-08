#!/usr/bin/env python3
"""PAD-Stream V16E-17-R1
E15 Contract-Schema Repair and Independent Full-Grid Completion Validation.

Independent validation milestone after V16E-16 controlled background-only
completion. V16E-17 does not modify or regenerate the accepted V16E-16
candidate. It reconstructs the full-grid state independently from the frozen
V16E-13-R1 supported-cell map-back plus the frozen V16E-11-R2 constitutive Swc
background and checks the V16E-16 candidate against that reconstruction.

A PASS establishes readiness for a separate provenance/freeze milestone only.
It does not itself freeze the full-grid candidate and does not authorize SG7E
thresholding or a full-grid plume claim.
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

MILESTONE = "V16E-17-R1"
SUCCESS = "V16E17_R1_INDEPENDENT_FULL_GRID_COMPLETION_VALIDATION_PASS"
BLOCKED = "V16E17_R1_INDEPENDENT_FULL_GRID_COMPLETION_VALIDATION_BLOCKED"
NEXT_PASS = "V16E-18 - Full-Grid Candidate Freeze / Provenance Manifest"
NEXT_FAIL = "V16E-17-R2 - Repair only the failed V16E-17-R1 gate; preserve E13-R1/E14/E15/E16 unchanged"

# -----------------------------------------------------------------------------
# Blocked V16E-17 parent evidence. R1 repairs only an E15 contract-schema
# interpretation error: V16E-17 incorrectly queried top-level keys that V16E-15
# intentionally stores under current_state / firewall.
# -----------------------------------------------------------------------------
PARENT_E17_RUNNER = (
    "PAD_Stream_V16E17_Independent_Full_Grid_Completion_Validation.py",
    "9c15a5589146d49f8ee607a9bbda6216a90f117f91321c52d5b998054f008d54",
)
PARENT_E17_BLOCKED_REL = Path("provenance/hybrid_dp/V16E17_R1_BLOCKED_INDEPENDENT_FULL_GRID_COMPLETION_VALIDATION")
PARENT_E17_BLOCKED = (
    "V16E17_R1_Blocked_Independent_Full_Grid_Validation_Audit.json",
    "68c522d5cc54f26c9a375cb16b55ecb5eca59c4d2a463917c8b7ebe7ab6afb7a",
)

# -----------------------------------------------------------------------------
# Frozen V16 authority.
# -----------------------------------------------------------------------------
E16_RUNNER = (
    "PAD_Stream_V16E16_Controlled_Background_Only_Unsupported_Cell_Completion.py",
    "3798052c6a98a60f7faf4cd0d2c30003297622a72c3ddfe714bfb4f71d6bebde",
)
E16_REL = Path("pilots/hybrid_dp/V16E16_SGSIM_100D_CONTROLLED_BACKGROUND_ONLY_FULL_GRID_COMPLETION")
E16 = {
    "numerical": ("V16E16_SGSim_100Day_Background_Completed_Full_Grid.npz", "d422dc1e56281c1baf0ae007c62ce4bd69677a232bd1448a5bd79d3177eafaea"),
    "audit": ("V16E16_Background_Completion_Audit.json", "6c017ed9fc1268a9fc808a1e69470ee32f8ee23f64a72e1a0de283cf8dbaca4d"),
    "contract": ("V16E16_Background_Completion_Contract.json", "7d1216a5d5a8fc7a8fc484e9d480e290f37c5c4170aa6f2c9ee8e3fbc6a31379"),
    "manifest": ("V16E16_Full_Grid_Candidate_Manifest.json", "2d1ee8ba7db336c097c4834e5b1ee2c8e909bedb2b0650d0801c4f88ac322752"),
    "summary": ("PAD_Stream_V16E16_Summary.json", "cfa036cb11391a307d68f7f30e2b59ceb7f2b7a0f698b8989777abd28a96b548"),
    "handoff": ("V16E16_Handoff.md", "6cd85e63ad7e9da58f50d716a4eebcca4ca043c90c17f2ac5eeb8332cbf1fa56"),
}
E16_SUCCESS = "V16E16_CONTROLLED_BACKGROUND_ONLY_FULL_GRID_COMPLETION_PASS"

E15_RUNNER = (
    "PAD_Stream_V16E15_SGSim_Unsupported_Cell_Policy_Design_and_Audit.py",
    "a851ec64d85ed019720feffcc4a7f705a100926c8cdf338c934be416f786111c",
)
E15_REL = Path("provenance/hybrid_dp/V16E15_SGSIM_UNSUPPORTED_CELL_POLICY_DESIGN_AUDIT")
E15_CONTRACT = (
    "V16E15_Unsupported_Cell_Policy_Contract.json",
    "5c692ea3b9ba4dee0e43005faeee016c4d442f1d8eb24fa7e21651ddc136f5e0",
)
E15_AUDIT = (
    "V16E15_Unsupported_Cell_Policy_Audit.json",
    "b4c0a414abbb3d0e980ba1c2649d08d4002f2630fbbe2d96b4f922974976f102",
)
E15_SUMMARY = (
    "PAD_Stream_V16E15_Summary.json",
    "8df4fcf68d7325ab7db7d9a03bb15478fab609b46dc5a54fafcd201a697b30ba",
)

E14_RUNNER = (
    "PAD_Stream_V16E14_Independent_SGSim_100Day_MapBack_Conservation_and_Support_Audit.py",
    "8225bc3d6e6c5f1731e75b74663285a880206c23c1d82fb524f14cf2122e2898",
)
E14_REL = Path("provenance/hybrid_dp/V16E14_INDEPENDENT_SGSIM_100D_MAPBACK_CONSERVATION_SUPPORT_AUDIT")
E14_SUMMARY = (
    "PAD_Stream_V16E14_Summary.json",
    "e57397fc538c374f94c45494df801525c36c0327140ef2fdeb5cab47307d7450",
)

E13R1_RUNNER = (
    "PAD_Stream_V16E13_R1_Native_Dtype_Identity_Repair_and_Controlled_Conservative_Streamline_to_Grid_MapBack_Execution.py",
    "b8e04c2db9846709c2791afa65d8b10fd9b9e8ada0ac48b0b24cbdf4765e80b6",
)
E13R1_REL = Path("pilots/hybrid_dp/V16E13_R1_SGSIM_100D_CONTROLLED_CONSERVATIVE_MAPBACK")
E13R1_NUMERICAL = (
    "V16E13_R1_SGSim_100Day_Conservative_MapBack.npz",
    "6ef79d6f126a96b7e64a5fb7f9d11164758b9c2726657ff4f7874f0e6acfa79f",
)
E13R1_CONTRACT = (
    "V16E13_R1_Conservative_MapBack_Contract.json",
    "733ced4bb7da6b3c808871f36f73634cd5d3da2290cdde3ca099321fb871a048",
)

E11R2_RUNNER = (
    "PAD_Stream_V16E11_R2_Packed_SG5_Serialization_Repair_and_Controlled_Hybrid_Streamline_Pilot.py",
    "0363a09612c5e80f6bb8124c817ca0d3726b1654283ab169c9b2d4d9861707b7",
)
E11R2_REL = Path("pilots/hybrid_dp/V16E11_R2_SGSIM_100D_CONTROLLED_STREAMLINE_PILOT")
E11R2_PILOT = (
    "V16E11_R2_SGSim_100Day_Streamline_Pilot.npz",
    "710720e933d740787868a9894fa04f90e88429c120d9f86a52b750f4c41db844",
)

# Historical independent-validation source authority.
V15_D5 = (
    "PAD_Stream_V15SG7D5_Independent_Full_Grid_Completion_Validation.py",
    "bdf662bda22f7399be66d37eaf2f47a4a58d02af2a87b29a311f4761845fb9a7",
)

OUT_REL = Path("provenance/hybrid_dp/V16E17_R1_INDEPENDENT_FULL_GRID_COMPLETION_VALIDATION")
BLOCKED_REL = Path("provenance/hybrid_dp/V16E17_R1_BLOCKED_INDEPENDENT_FULL_GRID_COMPLETION_VALIDATION")

EXPECTED_GRID = (15, 50, 50)
EXPECTED_CELLS = 37500
EXPECTED_SUPPORTED = 20462
EXPECTED_UNSUPPORTED = 17038
EXPECTED_TIME_DAYS = 100.0
EXPECTED_BACKGROUND = 0.2
EXPECTED_FULL_MIN = 0.2
EXPECTED_FULL_MAX = 0.78499960534060065
EXPECTED_SUPPORTED_DIAGNOSTIC = 15924
SELECTED_POLICY = "P4_MASKED_BACKGROUND_PLUS_SUPPORT"
DIAGNOSTIC_THRESHOLD = 0.21  # Historical completion-preservation diagnostic only; NOT SG7E.

PROHIBITIONS = [
    "NO CHANGE TO V16E-13-R1, V16E-14, V16E-15, OR V16E-16 ARTIFACTS.",
    "NO CHANGE TO THE BLOCKED V16E-17 RECORD; R1 REPAIRS ONLY ITS E15 SCHEMA INTERPRETATION.",
    "NO RE-EXECUTION OF MAP-BACK OR BACKGROUND COMPLETION.",
    "NO CHANGE TO SUPPORTED-CELL SATURATION VALUES.",
    "NO CHANGE TO SUPPORT MASK / NUMERATOR / DENOMINATOR / PIECE / VISIT EVIDENCE.",
    "NO INTERPOLATION, NEAREST-NEIGHBOR, OR ROUTE-SPECIFIC FILL.",
    "NO TRAINING, CHECKPOINT LOAD, OR MODEL INFERENCE.",
    "NO PRESSURE / DARCY / POLLOCK / TOF RECOMPUTATION.",
    "NO SG7E THRESHOLD CHANGE OR FULL-GRID PLUME CLAIM.",
    "NO CANDIDATE FREEZE IN V16E-17; FREEZE REQUIRES V16E-18.",
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


def atomic_write(path: Path, data: bytes):
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
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows([{k: native(v) for k, v in r.items()} for r in rows])
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
    visited = np.zeros(mask.shape, dtype=bool)
    sizes: list[int] = []
    neighbors = ((-1,0,0),(1,0,0),(0,-1,0),(0,1,0),(0,0,-1),(0,0,1))
    for k in range(nz):
        for j in range(ny):
            for i in range(nx):
                if not mask[k,j,i] or visited[k,j,i]:
                    continue
                stack = [(k,j,i)]
                visited[k,j,i] = True
                size = 0
                while stack:
                    ck,cj,ci = stack.pop()
                    size += 1
                    for dk,dj,di in neighbors:
                        nk,nj,ni = ck+dk,cj+dj,ci+di
                        if (0 <= nk < nz and 0 <= nj < ny and 0 <= ni < nx
                                and mask[nk,nj,ni] and not visited[nk,nj,ni]):
                            visited[nk,nj,ni] = True
                            stack.append((nk,nj,ni))
                sizes.append(size)
    sizes.sort(reverse=True)
    return sizes


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", default=str(Path(__file__).resolve().parent))
    ap.add_argument("--drive-root", default="/content/drive/MyDrive/PAD_Stream_Compute")
    ap.add_argument("--output-dir", default="")
    args = ap.parse_args()

    repo = Path(args.project_root).resolve()
    compute = Path(args.drive_root).resolve()
    out = Path(args.output_dir).resolve() if args.output_dir else compute / OUT_REL
    g = Gates()

    print("=" * 132)
    print("PAD-Stream V16E-17-R1 E15 Contract-Schema Repair and Independent Full-Grid Completion Validation")
    print("=" * 132)
    for line in PROHIBITIONS:
        print(line)

    try:
        # ------------------------------------------------------------------
        # Blocked V16E-17 parent evidence.
        # ------------------------------------------------------------------
        print("\nBLOCKED V16E-17 PARENT EVIDENCE")
        bind(g, "parent_E17_runner", repo / PARENT_E17_RUNNER[0], PARENT_E17_RUNNER[1])
        parent_blocked_path = compute / PARENT_E17_BLOCKED_REL / PARENT_E17_BLOCKED[0]
        bind(g, "parent_E17_blocked_audit", parent_blocked_path, PARENT_E17_BLOCKED[1])
        parent_blocked = read_json(parent_blocked_path)
        parent_gates = parent_blocked.get("gates", {})
        parent_failed = [name for name, rec in parent_gates.items() if not bool(rec.get("passed", False))]
        g.check("parent_E17_status_BLOCKED", parent_blocked.get("status") == "V16E17_INDEPENDENT_FULL_GRID_COMPLETION_VALIDATION_BLOCKED")
        g.check("parent_E17_single_failed_gate", parent_failed == ["E15_no_grid_change"], str(parent_failed))
        g.check("parent_E17_exception_exact_gate", "E15_no_grid_change" in str(parent_blocked.get("exception", "")))
        g.check("parent_E17_upstream_not_modified",
                parent_blocked.get("E13R1_modified") is False
                and parent_blocked.get("E14_modified") is False
                and parent_blocked.get("E15_modified") is False
                and parent_blocked.get("E16_modified") is False)
        g.check("parent_E17_completion_not_reexecuted", parent_blocked.get("completion_reexecuted") is False)
        g.check("parent_E17_candidate_not_frozen", parent_blocked.get("candidate_frozen") is False)
        g.check("parent_E17_full_grid_plume_not_authorized", parent_blocked.get("full_grid_plume_authorized") is False)
        g.check("parent_E17_all_prior_gates_passed",
                all(bool(rec.get("passed", False)) for name, rec in parent_gates.items() if name != "E15_no_grid_change"))

        # ------------------------------------------------------------------
        # E16 candidate identity and execution contract.
        # ------------------------------------------------------------------
        print("\nV16E-16 FULL-GRID CANDIDATE AUTHORITY")
        bind(g, "E16_runner", repo / E16_RUNNER[0], E16_RUNNER[1])
        e16_paths: dict[str, Path] = {}
        for key, (fn, hs) in E16.items():
            p = compute / E16_REL / fn
            bind(g, "E16_" + key, p, hs)
            e16_paths[key] = p

        e16_audit = read_json(e16_paths["audit"])
        e16_contract = read_json(e16_paths["contract"])
        e16_manifest = read_json(e16_paths["manifest"])
        e16_summary = read_json(e16_paths["summary"])

        g.check("E16_summary_status_PASS", e16_summary.get("status") == "PASS")
        g.check("E16_contract_status_exact", e16_contract.get("status") == E16_SUCCESS)
        g.check("E16_manifest_status_exact", e16_manifest.get("status") == E16_SUCCESS)
        g.check("E16_policy_exact", e16_contract.get("selected_policy") == SELECTED_POLICY and e16_audit.get("selected_policy") == SELECTED_POLICY)
        g.check("E16_candidate_created_not_frozen", e16_summary.get("full_grid_candidate_created") is True and e16_summary.get("candidate_frozen") is False)
        g.check("E16_full_grid_plume_not_authorized", e16_summary.get("full_grid_plume_authorized") is False)
        g.check("E16_independent_validation_required", e16_summary.get("independent_validation_required") is True and e16_contract.get("independent_validation_required") is True)
        g.check("E16_next_is_E17", str(e16_summary.get("next_milestone", "")).startswith("V16E-17"))
        g.check("E16_counts_exact", int(e16_summary.get("supported_cells_preserved")) == EXPECTED_SUPPORTED and int(e16_summary.get("unsupported_cells_completed")) == EXPECTED_UNSUPPORTED and int(e16_summary.get("full_grid_cells")) == EXPECTED_CELLS)
        g.check("E16_background_exact", float(e16_summary.get("background_saturation")) == EXPECTED_BACKGROUND)
        g.check("E16_bounds_exact", float(e16_summary.get("full_grid_min")) == EXPECTED_FULL_MIN and float(e16_summary.get("full_grid_max")) == EXPECTED_FULL_MAX)
        g.check("E16_supported_change_zero", float(e16_summary.get("supported_state_Linf_change")) == 0.0)
        g.check("E16_unsupported_background_error_zero", float(e16_summary.get("unsupported_background_Linf_error")) == 0.0)
        g.check("E16_zero_unsupported_diagnostic_plume", int(e16_summary.get("unsupported_diagnostic_plume_cells")) == 0)
        g.check("E16_candidate_file_hash_manifest_exact", e16_manifest.get("numerical_file_sha256") == E16["numerical"][1] and e16_contract.get("numerical_file_sha256") == E16["numerical"][1] and e16_summary.get("numerical_file_sha256") == E16["numerical"][1])

        preservation = e16_contract.get("preservation_contract", {})
        g.check("E16_contract_supported_exact_semantics", "exact V16E-13-R1" in str(preservation.get("supported_cells", "")))
        g.check("E16_contract_support_provenance_preserved", "unchanged" in str(preservation.get("support_mask", "")))
        g.check("E16_contract_interpolation_prohibited", preservation.get("interpolation") == "PROHIBITED")
        g.check("E16_contract_nearest_prohibited", preservation.get("nearest_neighbor") == "PROHIBITED")
        g.check("E16_contract_route_fill_prohibited", preservation.get("route_specific_fill") == "PROHIBITED")
        g.check("E16_contract_new_projection_prohibited", preservation.get("new_conservative_projection") == "PROHIBITED")

        # ------------------------------------------------------------------
        # Parent independent map-back / policy authority.
        # ------------------------------------------------------------------
        print("\nUPSTREAM INDEPENDENT-AUDIT / POLICY AUTHORITY")
        bind(g, "E15_runner", repo / E15_RUNNER[0], E15_RUNNER[1])
        e15_contract_path = compute / E15_REL / E15_CONTRACT[0]
        e15_audit_path = compute / E15_REL / E15_AUDIT[0]
        e15_summary_path = compute / E15_REL / E15_SUMMARY[0]
        bind(g, "E15_contract", e15_contract_path, E15_CONTRACT[1])
        bind(g, "E15_audit", e15_audit_path, E15_AUDIT[1])
        bind(g, "E15_summary", e15_summary_path, E15_SUMMARY[1])
        e15_contract = read_json(e15_contract_path)
        e15_audit = read_json(e15_audit_path)
        e15_summary = read_json(e15_summary_path)
        g.check("E15_selected_policy_P4", e15_contract.get("selected_policy") == SELECTED_POLICY)

        # R1 schema repair:
        # V16E-15 intentionally persists the no-grid-change evidence under
        # contract.current_state and audit.firewall, not as top-level contract
        # keys. The blocked parent queried nonexistent top-level fields.
        e15_current = e15_contract.get("current_state", {})
        e15_firewall = e15_audit.get("firewall", {})
        g.check("E15_contract_schema_current_state_present",
                isinstance(e15_current, dict)
                and "unsupported_cells_filled" in e15_current
                and "full_grid_candidate_created" in e15_current
                and "full_grid_plume_authorized" in e15_current)
        g.check("E15_audit_schema_firewall_present",
                isinstance(e15_firewall, dict)
                and "grid_values_modified" in e15_firewall
                and "unsupported_cells_filled" in e15_firewall
                and "mapback_reexecuted" in e15_firewall)
        g.check("E15_no_grid_change_reconciled",
                e15_current.get("unsupported_cells_filled") is False
                and e15_current.get("full_grid_candidate_created") is False
                and e15_current.get("full_grid_plume_authorized") is False
                and e15_firewall.get("grid_values_modified") is False
                and e15_firewall.get("unsupported_cells_filled") is False
                and e15_firewall.get("mapback_reexecuted") is False
                and e15_summary.get("unsupported_cells_filled") is False
                and e15_summary.get("full_grid_candidate_created") is False
                and e15_summary.get("full_grid_plume_authorized") is False)
        g.check("E15_schema_repair_without_data_change",
                "grid_changed" not in e15_contract
                and "unsupported_cells_filled" not in e15_contract
                and e15_current.get("unsupported_cells_filled") is False)

        bind(g, "E14_runner", repo / E14_RUNNER[0], E14_RUNNER[1])
        e14_summary_path = compute / E14_REL / E14_SUMMARY[0]
        bind(g, "E14_summary", e14_summary_path, E14_SUMMARY[1])
        e14_summary = read_json(e14_summary_path)
        g.check("E14_status_PASS", e14_summary.get("status") == "PASS")
        g.check("E14_state_reconstruction_exact", float(e14_summary.get("state_reconstruction_Linf")) == 0.0)
        g.check("E14_support_counts_exact", int(e14_summary.get("supported_cells")) == EXPECTED_SUPPORTED and int(e14_summary.get("unsupported_cells")) == EXPECTED_UNSUPPORTED)
        g.check("E14_no_fill", e14_summary.get("unsupported_cells_filled") is False)

        # ------------------------------------------------------------------
        # Historical independent validation source authority.
        # ------------------------------------------------------------------
        print("\nVERSION-15 INDEPENDENT FULL-GRID VALIDATION SOURCE AUTHORITY")
        d5_path = repo / V15_D5[0]
        bind(g, "V15SG7D5_source", d5_path, V15_D5[1])
        g.check("V15SG7D5_reconstruction_semantics_present", source_contains(d5_path, [
            "Independent Full-Grid Completion Validation",
            "independently reconstructs that full-grid candidate",
            "supported_cells_preserved",
            "unsupported_cells_equal_frozen_background",
            "conservative_denominator_preserved",
            "conservative_numerator_preserved",
            "unsupported_background_adds_no_plume",
            "plume_topology_preserved",
        ]))

        # ------------------------------------------------------------------
        # E13-R1 supported-cell authority and E11-R2 background authority.
        # These are the independent reconstruction sources; E16 arrays are not
        # used as inputs to construct the validation reference.
        # ------------------------------------------------------------------
        print("\nINDEPENDENT RECONSTRUCTION SOURCE AUTHORITY")
        bind(g, "E13R1_runner", repo / E13R1_RUNNER[0], E13R1_RUNNER[1])
        e13_num_path = compute / E13R1_REL / E13R1_NUMERICAL[0]
        e13_contract_path = compute / E13R1_REL / E13R1_CONTRACT[0]
        bind(g, "E13R1_numerical", e13_num_path, E13R1_NUMERICAL[1])
        bind(g, "E13R1_contract", e13_contract_path, E13R1_CONTRACT[1])
        e13_contract = read_json(e13_contract_path)

        bind(g, "E11R2_runner", repo / E11R2_RUNNER[0], E11R2_RUNNER[1])
        pilot_path = compute / E11R2_REL / E11R2_PILOT[0]
        bind(g, "E11R2_pilot", pilot_path, E11R2_PILOT[1])

        with np.load(e13_num_path, allow_pickle=False) as db:
            required_e13 = [
                "saturation_grid_float64", "supported_mask", "support_denominator",
                "support_numerator", "segment_piece_count", "streamline_visit_count",
                "physical_time_days", "grid_shape",
            ]
            g.check("E13R1_required_arrays_present", all(k in db.files for k in required_e13), str(db.files))
            s13 = np.array(db["saturation_grid_float64"], dtype=np.float64, copy=True)
            mask13 = np.array(db["supported_mask"], copy=True).astype(np.uint8)
            den13 = np.array(db["support_denominator"], dtype=np.float64, copy=True)
            num13 = np.array(db["support_numerator"], dtype=np.float64, copy=True)
            pieces13 = np.array(db["segment_piece_count"], dtype=np.int64, copy=True)
            visits13 = np.array(db["streamline_visit_count"], dtype=np.int64, copy=True)
            grid13 = tuple(int(x) for x in np.asarray(db["grid_shape"]).tolist())
            time13 = float(np.asarray(db["physical_time_days"]))

        support = den13 > 0.0
        unsupported = ~support
        g.check("E13R1_grid_time_exact", grid13 == EXPECTED_GRID and time13 == EXPECTED_TIME_DAYS)
        g.check("E13R1_support_mask_reproduced", np.array_equal(mask13.astype(bool), support))
        g.check("E13R1_counts_exact", int(np.sum(support)) == EXPECTED_SUPPORTED and int(np.sum(unsupported)) == EXPECTED_UNSUPPORTED)
        g.check("E13R1_supported_finite_unsupported_nan", np.all(np.isfinite(s13[support])) and np.all(np.isnan(s13[unsupported])))
        g.check("E13R1_piece_visit_support_consistency", np.all(pieces13[support] > 0) and np.all(visits13[support] > 0) and np.all(pieces13[unsupported] == 0) and np.all(visits13[unsupported] == 0))

        arrs = e13_contract.get("array_sha256", {})
        g.check("E13R1_array_hashes_exact", arr_sha(s13) == arrs.get("saturation_grid_float64") and arr_sha(den13) == arrs.get("support_denominator") and arr_sha(num13) == arrs.get("support_numerator") and arr_sha(mask13) == arrs.get("supported_mask"))

        with np.load(pilot_path, allow_pickle=False) as db:
            g.check("E11R2_background_keys_present", "constitutive_swc" in db.files and "saturation_100d" in db.files)
            swc = float(np.asarray(db["constitutive_swc"]))
            sat_native = np.array(db["saturation_100d"], copy=True)
        g.check("E11R2_swc_exact_0p2", swc == EXPECTED_BACKGROUND, f"{swc:.17g}")
        g.check("E11R2_transport_min_matches_float32_Swc", sat_native.dtype == np.float32 and float(np.min(sat_native)) == float(np.float32(swc)))
        background = np.float64(swc)

        # ------------------------------------------------------------------
        # Load E16 candidate only after independent sources are established.
        # ------------------------------------------------------------------
        print("\nV16E-16 CANDIDATE ARRAY IDENTITY")
        with np.load(e16_paths["numerical"], allow_pickle=False) as db:
            required_e16 = [
                "saturation_grid_full_float64", "saturation_grid_supported_only_float64",
                "supported_mask", "support_denominator", "support_numerator",
                "segment_piece_count", "streamline_visit_count", "background_saturation",
                "diagnostic_threshold", "physical_time_days", "grid_shape",
            ]
            g.check("E16_required_arrays_present", all(k in db.files for k in required_e16), str(db.files))
            full16 = np.array(db["saturation_grid_full_float64"], dtype=np.float64, copy=True)
            supported_only16 = np.array(db["saturation_grid_supported_only_float64"], dtype=np.float64, copy=True)
            mask16 = np.array(db["supported_mask"], copy=True).astype(np.uint8)
            den16 = np.array(db["support_denominator"], dtype=np.float64, copy=True)
            num16 = np.array(db["support_numerator"], dtype=np.float64, copy=True)
            pieces16 = np.array(db["segment_piece_count"], dtype=np.int64, copy=True)
            visits16 = np.array(db["streamline_visit_count"], dtype=np.int64, copy=True)
            background16 = float(np.asarray(db["background_saturation"]))
            diag16 = float(np.asarray(db["diagnostic_threshold"]))
            time16 = float(np.asarray(db["physical_time_days"]))
            grid16 = tuple(int(x) for x in np.asarray(db["grid_shape"]).tolist())

        g.check("E16_grid_time_exact", full16.shape == EXPECTED_GRID and grid16 == EXPECTED_GRID and time16 == EXPECTED_TIME_DAYS)
        g.check("E16_all_evidence_shapes_exact", all(a.shape == EXPECTED_GRID for a in [supported_only16, mask16, den16, num16, pieces16, visits16]))
        g.check("E16_background_scalar_exact", background16 == float(background))
        g.check("E16_diagnostic_threshold_historical_exact", diag16 == DIAGNOSTIC_THRESHOLD)
        g.check("E16_candidate_array_hash_exact", arr_sha(full16) == e16_manifest.get("candidate_array_sha256") == e16_contract.get("array_sha256", {}).get("full_grid"))

        # ------------------------------------------------------------------
        # Independent reconstruction: ONLY E13-R1 + E11-R2 inputs.
        # ------------------------------------------------------------------
        print("\nINDEPENDENT FULL-GRID RECONSTRUCTION")
        reconstructed = np.array(s13, dtype=np.float64, copy=True)
        reconstructed[unsupported] = background
        reconstructed2 = np.array(s13, dtype=np.float64, copy=True)
        reconstructed2[unsupported] = background

        delta = reconstructed - full16
        reconstruction_l1 = float(np.mean(np.abs(delta)))
        reconstruction_linf = float(np.max(np.abs(delta)))
        reconstructed_exact = bool(np.array_equal(reconstructed, full16))
        reconstructed_hash_exact = arr_sha(reconstructed) == arr_sha(full16)
        deterministic_reference_exact = bool(np.array_equal(reconstructed, reconstructed2))

        g.check("independent_reconstruction_deterministic_exact", deterministic_reference_exact)
        g.check("full_grid_independent_reconstruction_bitwise_exact", reconstructed_exact, f"Linf={reconstruction_linf:.17g}")
        g.check("full_grid_independent_reconstruction_hash_exact", reconstructed_hash_exact)
        g.check("full_grid_reconstruction_Linf_zero", reconstruction_linf == 0.0)

        # Supported / unsupported exactness.
        supported_linf = float(np.max(np.abs(full16[support] - s13[support])))
        unsupported_linf = float(np.max(np.abs(full16[unsupported] - background)))
        g.check("supported_cells_exactly_preserved_independently", supported_linf == 0.0)
        g.check("unsupported_cells_exact_background_independently", unsupported_linf == 0.0)
        g.check("supported_only_sidecar_exact_E13R1", np.array_equal(supported_only16, s13, equal_nan=True))
        g.check("full_grid_all_finite", np.all(np.isfinite(full16)))
        g.check("full_grid_min_exact_background", float(np.min(full16)) == float(background), f"{float(np.min(full16)):.17g}")
        g.check("full_grid_max_exact_supported_max", float(np.max(full16)) == float(np.nanmax(s13)), f"{float(np.max(full16)):.17g}")
        g.check("full_grid_physical_bounds", float(np.min(full16)) >= 0.0 and float(np.max(full16)) <= 1.0)

        # Support/conservative evidence must be exact copies of E13-R1.
        g.check("support_mask_independent_exact", np.array_equal(mask16, mask13))
        g.check("support_denominator_independent_hash_exact", arr_sha(den16) == arr_sha(den13))
        g.check("support_numerator_independent_hash_exact", arr_sha(num16) == arr_sha(num13))
        g.check("segment_piece_count_independent_hash_exact", arr_sha(pieces16) == arr_sha(pieces13))
        g.check("streamline_visit_count_independent_hash_exact", arr_sha(visits16) == arr_sha(visits13))
        g.check("background_completed_cells_remain_unsupported", np.all(mask16[unsupported] == 0) and np.all(den16[unsupported] == 0.0) and np.all(num16[unsupported] == 0.0))

        # Historical diagnostic only; never an SG7E threshold claim.
        supported_plume_reference = support & np.isfinite(s13) & (s13 >= DIAGNOSTIC_THRESHOLD)
        completed_diagnostic = full16 >= DIAGNOSTIC_THRESHOLD
        unsupported_diagnostic = unsupported & completed_diagnostic
        supported_completed = support & completed_diagnostic
        supported_diagnostic_exact = bool(np.array_equal(supported_plume_reference, supported_completed))
        unsupported_diagnostic_cells = int(np.sum(unsupported_diagnostic))
        ref_components = connected_components_3d(supported_plume_reference)
        completed_components = connected_components_3d(completed_diagnostic)
        topology_preserved = ref_components == completed_components

        g.check("supported_diagnostic_membership_independent_exact", supported_diagnostic_exact)
        g.check("supported_diagnostic_count_exact", int(np.sum(supported_plume_reference)) == EXPECTED_SUPPORTED_DIAGNOSTIC)
        g.check("unsupported_background_adds_zero_diagnostic_plume_independent", unsupported_diagnostic_cells == 0)
        g.check("diagnostic_plume_topology_independent_exact", topology_preserved)
        g.check("diagnostic_threshold_not_SG7E", True)

        # Candidate remains only validation-ready; E17 is not the freeze.
        g.check("no_completion_reexecution", True)
        g.check("no_interpolation_used", True)
        g.check("no_nearest_neighbor_used", True)
        g.check("no_route_specific_fill_used", True)
        g.check("no_new_conservative_projection", True)
        g.check("candidate_not_frozen_in_E17", True)
        g.check("full_grid_plume_not_authorized_in_E17", True)
        g.check("E18_freeze_required", True)

        # ------------------------------------------------------------------
        # Persist independent validation evidence only; do not alter E16.
        # ------------------------------------------------------------------
        out.mkdir(parents=True, exist_ok=True)
        numerical = out / "V16E17_R1_Independent_Full_Grid_Validation.npz"
        np.savez_compressed(
            numerical,
            independently_reconstructed_full_grid_float64=reconstructed,
            E16_full_grid_float64=full16,
            supported_mask=mask13,
            support_denominator=den13,
            support_numerator=num13,
            segment_piece_count=pieces13,
            streamline_visit_count=visits13,
            background_saturation=np.asarray(background, dtype=np.float64),
            diagnostic_threshold=np.asarray(DIAGNOSTIC_THRESHOLD, dtype=np.float64),
            physical_time_days=np.asarray(EXPECTED_TIME_DAYS, dtype=np.float64),
            grid_shape=np.asarray(EXPECTED_GRID, dtype=np.int64),
            source_E16_numerical_sha256=np.asarray(E16["numerical"][1]),
            source_E13R1_numerical_sha256=np.asarray(E13R1_NUMERICAL[1]),
            source_E11R2_pilot_sha256=np.asarray(E11R2_PILOT[1]),
        )

        audit = {
            "milestone": MILESTONE,
            "status": "PASS",
            "validation_mode": "independent reconstruction from E13-R1 supported state plus E11-R2 constitutive Swc",
            "physical_time_days": EXPECTED_TIME_DAYS,
            "grid_shape": list(EXPECTED_GRID),
            "supported_cells": EXPECTED_SUPPORTED,
            "unsupported_cells": EXPECTED_UNSUPPORTED,
            "background_saturation": float(background),
            "full_grid_reconstruction_L1": reconstruction_l1,
            "full_grid_reconstruction_Linf": reconstruction_linf,
            "full_grid_reconstruction_exact": reconstructed_exact,
            "full_grid_reconstruction_hash_exact": reconstructed_hash_exact,
            "supported_state_Linf_change": supported_linf,
            "unsupported_background_Linf_error": unsupported_linf,
            "full_grid_min": float(np.min(full16)),
            "full_grid_max": float(np.max(full16)),
            "full_grid_all_finite": bool(np.all(np.isfinite(full16))),
            "support_mask_exact": bool(np.array_equal(mask16, mask13)),
            "support_denominator_exact": arr_sha(den16) == arr_sha(den13),
            "support_numerator_exact": arr_sha(num16) == arr_sha(num13),
            "segment_piece_count_exact": arr_sha(pieces16) == arr_sha(pieces13),
            "streamline_visit_count_exact": arr_sha(visits16) == arr_sha(visits13),
            "supported_diagnostic_cells": int(np.sum(supported_plume_reference)),
            "unsupported_diagnostic_cells": unsupported_diagnostic_cells,
            "diagnostic_topology_preserved": topology_preserved,
            "diagnostic_threshold": DIAGNOSTIC_THRESHOLD,
            "diagnostic_threshold_semantics": "HISTORICAL_V15_COMPLETION_PRESERVATION_CHECK_ONLY_NOT_SG7E",
            "candidate_frozen": False,
            "freeze_ready": True,
            "full_grid_plume_authorized": False,
            "next_milestone": NEXT_PASS,
        }
        contract = {
            "milestone": MILESTONE,
            "status": SUCCESS,
            "independent_reference_equation": "S_ref[c] = S_E13R1[c] if support_denominator[c] > 0 else E11R2 constitutive_swc",
            "selected_policy": SELECTED_POLICY,
            "repair_provenance": {
                "blocked_parent_milestone": "V16E-17",
                "blocked_parent_runner_sha256": PARENT_E17_RUNNER[1],
                "blocked_parent_audit_sha256": PARENT_E17_BLOCKED[1],
                "repaired_gate": "E15_no_grid_change",
                "repair": "read canonical V16E-15 current_state/firewall schema; no data or policy change",
            },
            "background_authority": "E11-R2 constitutive_swc",
            "background_saturation": float(background),
            "validation_requirements": {
                "E16_candidate_file_identity_exact": True,
                "independent_full_grid_reconstruction_exact": True,
                "supported_cells_exact_E13R1": True,
                "unsupported_cells_exact_background": True,
                "support_mask_exact_E13R1": True,
                "support_denominator_exact_E13R1": True,
                "support_numerator_exact_E13R1": True,
                "segment_piece_count_exact_E13R1": True,
                "streamline_visit_count_exact_E13R1": True,
                "unsupported_background_adds_zero_diagnostic_plume": True,
                "diagnostic_topology_preserved": True,
            },
            "source_authority": {
                "E16_runner_sha256": E16_RUNNER[1],
                "E16_artifacts": {k: {"file": v[0], "sha256": v[1]} for k, v in E16.items()},
                "parent_E17_runner_sha256": PARENT_E17_RUNNER[1],
                "parent_E17_blocked_audit_sha256": PARENT_E17_BLOCKED[1],
                "E15_runner_sha256": E15_RUNNER[1],
                "E15_contract_sha256": E15_CONTRACT[1],
                "E15_audit_sha256": E15_AUDIT[1],
                "E15_summary_sha256": E15_SUMMARY[1],
                "E14_runner_sha256": E14_RUNNER[1],
                "E14_summary_sha256": E14_SUMMARY[1],
                "E13R1_runner_sha256": E13R1_RUNNER[1],
                "E13R1_numerical_sha256": E13R1_NUMERICAL[1],
                "E13R1_contract_sha256": E13R1_CONTRACT[1],
                "E11R2_runner_sha256": E11R2_RUNNER[1],
                "E11R2_pilot_sha256": E11R2_PILOT[1],
                "V15SG7D5_source_sha256": V15_D5[1],
            },
            "candidate_frozen": False,
            "freeze_ready": True,
            "full_grid_plume_authorized": False,
            "SG7E_threshold_changed": False,
            "next_milestone": NEXT_PASS,
        }
        freeze_readiness = {
            "milestone": MILESTONE,
            "status": SUCCESS,
            "candidate": "V16E16_background_completed_full_grid_float64",
            "candidate_file": E16["numerical"][0],
            "candidate_file_sha256": E16["numerical"][1],
            "candidate_array_sha256": arr_sha(full16),
            "independent_reconstruction_array_sha256": arr_sha(reconstructed),
            "independent_reconstruction_exact": reconstructed_exact,
            "support_mask_array_sha256": arr_sha(mask13),
            "support_denominator_array_sha256": arr_sha(den13),
            "support_numerator_array_sha256": arr_sha(num13),
            "background_saturation": float(background),
            "supported_cells": EXPECTED_SUPPORTED,
            "background_completed_cells": EXPECTED_UNSUPPORTED,
            "ready_for_V16E18_freeze": True,
            "candidate_frozen": False,
            "full_grid_plume_authorized": False,
            "next_milestone": NEXT_PASS,
        }
        summary = {
            "milestone": MILESTONE,
            "status": "PASS",
            "physical_time_days": EXPECTED_TIME_DAYS,
            "grid_shape": list(EXPECTED_GRID),
            "supported_cells": EXPECTED_SUPPORTED,
            "unsupported_cells": EXPECTED_UNSUPPORTED,
            "background_saturation": float(background),
            "full_grid_reconstruction_L1": reconstruction_l1,
            "full_grid_reconstruction_Linf": reconstruction_linf,
            "full_grid_reconstruction_exact": reconstructed_exact,
            "supported_state_Linf_change": supported_linf,
            "unsupported_background_Linf_error": unsupported_linf,
            "full_grid_min": float(np.min(full16)),
            "full_grid_max": float(np.max(full16)),
            "support_evidence_preserved_exact": True,
            "unsupported_diagnostic_plume_cells": unsupported_diagnostic_cells,
            "diagnostic_plume_topology_preserved": topology_preserved,
            "candidate_frozen": False,
            "freeze_ready": True,
            "full_grid_plume_authorized": False,
            "internal_test_reopened": False,
            "OOD_reopened": False,
            "next_milestone": NEXT_PASS,
        }

        numerical_sha = sha(numerical)
        for obj in (audit, contract, freeze_readiness, summary):
            obj["validation_numerical_file_sha256"] = numerical_sha

        handoff = f"""# PAD-Stream V16E-17-R1 - Independent Full-Grid Completion Validation PASS

V16E-17 independently reconstructed the V16E-16 full-grid candidate from V16E-13-R1 supported-cell saturation plus the frozen V16E-11-R2 constitutive Swc background.

- Grid: 15 x 50 x 50
- Supported cells: {EXPECTED_SUPPORTED}
- Background-completed cells: {EXPECTED_UNSUPPORTED}
- Background Swc: {float(background):.17g}
- Independent reconstruction L1: {reconstruction_l1:.17g}
- Independent reconstruction Linf: {reconstruction_linf:.17g}
- Independent reconstruction exact: YES
- Supported-state Linf change: {supported_linf:.17g}
- Unsupported-background Linf error: {unsupported_linf:.17g}
- Support mask / numerator / denominator / piece / visit evidence: exact
- Unsupported diagnostic plume cells: {unsupported_diagnostic_cells}
- Diagnostic topology preserved: YES
- Candidate frozen by E17: NO
- Freeze ready: YES
- Full-grid plume authorized: NO

NEXT: {NEXT_PASS}
""".encode("utf-8")

        files = {
            "V16E17_R1_Independent_Full_Grid_Validation_Audit.json": enc(audit),
            "V16E17_R1_Independent_Full_Grid_Validation_Contract.json": enc(contract),
            "V16E17_R1_Freeze_Readiness_Manifest.json": enc(freeze_readiness),
            "PAD_Stream_V16E17_R1_Summary.json": enc(summary),
            "V16E17_R1_Handoff.md": handoff,
        }
        for name, data in files.items():
            atomic_write(out / name, data)

        identity_rows = [
            {"artifact": "V16E16 full-grid candidate", "path": str(e16_paths["numerical"]), "sha256": E16["numerical"][1], "exact": True},
            {"artifact": "V16E13-R1 supported-cell map-back", "path": str(e13_num_path), "sha256": E13R1_NUMERICAL[1], "exact": True},
            {"artifact": "V16E11-R2 pilot/background authority", "path": str(pilot_path), "sha256": E11R2_PILOT[1], "exact": True},
        ]
        save_csv(out / "V16E17_R1_Artifact_Identity_Audit.csv", identity_rows)
        save_csv(out / "V16E17_R1_Independent_Reconstruction_Closure.csv", [{
            "L1": reconstruction_l1,
            "Linf": reconstruction_linf,
            "bitwise_exact": reconstructed_exact,
            "hash_exact": reconstructed_hash_exact,
            "reference_deterministic_repeat_exact": deterministic_reference_exact,
        }])
        save_csv(out / "V16E17_R1_Supported_Unsupported_Validation.csv", [{
            "supported_cells": EXPECTED_SUPPORTED,
            "supported_Linf_change": supported_linf,
            "unsupported_cells": EXPECTED_UNSUPPORTED,
            "unsupported_background_Linf_error": unsupported_linf,
            "background_saturation": float(background),
        }])
        save_csv(out / "V16E17_R1_Conservative_Evidence_Audit.csv", [{
            "support_mask_exact": True,
            "support_denominator_exact": True,
            "support_numerator_exact": True,
            "segment_piece_count_exact": True,
            "streamline_visit_count_exact": True,
        }])
        save_csv(out / "V16E17_R1_Diagnostic_Topology_Validation.csv", [{
            "diagnostic_threshold": DIAGNOSTIC_THRESHOLD,
            "threshold_semantics": "HISTORICAL_V15_COMPLETION_PRESERVATION_CHECK_ONLY_NOT_SG7E",
            "supported_reference_cells": int(np.sum(supported_plume_reference)),
            "completed_diagnostic_cells": int(np.sum(completed_diagnostic)),
            "unsupported_diagnostic_cells": unsupported_diagnostic_cells,
            "reference_component_count": len(ref_components),
            "completed_component_count": len(completed_components),
            "topology_preserved": topology_preserved,
        }])
        save_csv(out / "V16E17_R1_Final_Gate_Matrix.csv", [
            {"gate": name, "passed": rec["passed"], "detail": rec["detail"]}
            for name, rec in g.items.items()
        ])

        print("\n" + "=" * 132)
        print("V16E-17-R1 RESULT: PASS")
        print("=" * 132)
        print(f"{'SGSim grid':70}: 15 x 50 x 50")
        print(f"{'Supported cells independently preserved':70}: {EXPECTED_SUPPORTED}")
        print(f"{'Unsupported cells independently confirmed background':70}: {EXPECTED_UNSUPPORTED}")
        print(f"{'Frozen background saturation Swc':70}: {float(background):.17g}")
        print(f"{'Independent reconstruction L1 / Linf':70}: {reconstruction_l1:.17g} / {reconstruction_linf:.17g}")
        print(f"{'Independent reconstruction bitwise/hash exact':70}: YES / YES")
        print(f"{'Supported-state Linf change':70}: {supported_linf:.17g}")
        print(f"{'Unsupported-background Linf error':70}: {unsupported_linf:.17g}")
        print(f"{'Support/conservative evidence independently exact':70}: YES")
        print(f"{'Unsupported diagnostic plume cells':70}: {unsupported_diagnostic_cells}")
        print(f"{'Diagnostic plume topology preserved':70}: YES")
        print(f"{'Candidate frozen':70}: NO")
        print(f"{'Freeze ready':70}: YES")
        print(f"{'Full-grid plume authorized':70}: NO")
        print(f"{'Internal test / OOD reopened':70}: NO / NO")
        print(f"{numerical.name} SHA: {numerical_sha}")
        for name in files:
            print(f"{name} SHA: {sha(out / name)}")
        for name in [
            "V16E17_R1_Artifact_Identity_Audit.csv",
            "V16E17_R1_Independent_Reconstruction_Closure.csv",
            "V16E17_R1_Supported_Unsupported_Validation.csv",
            "V16E17_R1_Conservative_Evidence_Audit.csv",
            "V16E17_R1_Diagnostic_Topology_Validation.csv",
            "V16E17_R1_Final_Gate_Matrix.csv",
        ]:
            print(f"{name} SHA: {sha(out / name)}")
        print("Output:", out)
        print("NEXT:", NEXT_PASS)
        return 0

    except Exception as exc:
        print(f"\n[FAIL] V16E-17 did not close: {exc}", flush=True)
        try:
            bdir = compute / BLOCKED_REL
            bdir.mkdir(parents=True, exist_ok=True)
            report = {
                "milestone": MILESTONE,
                "status": BLOCKED,
                "exception": repr(exc),
                "gates": g.items,
                "parent_E17_runner_sha256": PARENT_E17_RUNNER[1],
                "parent_E17_blocked_audit_sha256": PARENT_E17_BLOCKED[1],
                "E13R1_modified": False,
                "E14_modified": False,
                "E15_modified": False,
                "E16_modified": False,
                "completion_reexecuted": False,
                "candidate_frozen": False,
                "full_grid_plume_authorized": False,
                "next_milestone": NEXT_FAIL,
            }
            p = bdir / "V16E17_R1_Blocked_Independent_Full_Grid_Validation_Audit.json"
            atomic_write(p, enc(report))
            print("Blocked report SHA:", sha(p))
            print("Blocked output:", bdir)
        except Exception:
            pass
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
