#!/usr/bin/env python3
"""PAD-Stream V16E-18
Full-Grid Candidate Freeze / Provenance Manifest.

Formal freeze milestone after V16E-17-R2 independently validated the V16E-16
background-completed 100-day SGSim full-grid candidate. E18 does not regenerate,
re-map, re-complete, interpolate, or otherwise alter the numerical field. It
copies the already validated V16E-16 candidate byte-for-byte into a frozen
location, verifies source/frozen SHA-256 identity, and records the complete
provenance and downstream deployment contract.

A PASS freezes the numerical candidate as the authoritative V16 100-day SGSim
full-grid deployment input. It does NOT authorize a full-grid plume claim and
does NOT establish or change any SG7E threshold.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any

import numpy as np

MILESTONE = "V16E-18"
SUCCESS = "V16E18_FULL_GRID_CANDIDATE_FREEZE_PASS"
BLOCKED = "V16E18_FULL_GRID_CANDIDATE_FREEZE_BLOCKED"
NEXT_PASS = "V16E-19 - Frozen Full-Grid Deployment Validation Contract / Baseline Audit"
NEXT_FAIL = "V16E-18-R1 - Repair only the failed V16E-18 freeze/provenance gate; preserve all numerical candidates unchanged"

# -----------------------------------------------------------------------------
# V16E-17-R2 independent validation authority.
# -----------------------------------------------------------------------------
E17R2_RUNNER = (
    "PAD_Stream_V16E17_R2_Blocked_Parent_Locator_Repair_and_Independent_Full_Grid_Completion_Validation.py",
    "a40ddb01dbbe40f7fffcc21203016b94e1b7b939a93d68a22f57360ae668b09e",
)
E17R2_REL = Path("provenance/hybrid_dp/V16E17_R2_INDEPENDENT_FULL_GRID_COMPLETION_VALIDATION")
E17R2 = {
    "numerical": ("V16E17_R2_Independent_Full_Grid_Validation.npz", "b3b055eac0c47367ea2982760627db6bea0584487daec50642eb5e6d6f6b9d46"),
    "audit": ("V16E17_R2_Independent_Full_Grid_Validation_Audit.json", "af395f845ac1c4441cc9e9aef3bc4d9d88d5c47c49ce660eb4d36becc2a98dc6"),
    "contract": ("V16E17_R2_Independent_Full_Grid_Validation_Contract.json", "b58f91a7cb4fa2349986262c335dacc968c5ed9252157ecda87412859c1c4d22"),
    "readiness": ("V16E17_R2_Freeze_Readiness_Manifest.json", "9a1ee30a47af214702059ed664286b2892b53fcff36a930d361547e0bca95063"),
    "summary": ("PAD_Stream_V16E17_R2_Summary.json", "96d0b86184cfdc35bed2f5dc11ff9769c0e9424ec6fcfba64ffe60a6676ae676"),
    "handoff": ("V16E17_R2_Handoff.md", "130ac6e4559a30e3e62d03875a99be550bab76ae4611415f3e7af7da8bd96894"),
    "identity_csv": ("V16E17_R2_Artifact_Identity_Audit.csv", "5011c4e6c9f8196356c9b39d16bd8faee6d40a85f99b22c25e2f73e1b3f46214"),
    "reconstruction_csv": ("V16E17_R2_Independent_Reconstruction_Closure.csv", "dc26e121cd35194a2410c0e0812d4faef6ef3a6572e3ab722189f98daa0ad6dc"),
    "supported_csv": ("V16E17_R2_Supported_Unsupported_Validation.csv", "bf834d9c030171e314e314db8ebe956cdf1db7712f5ce2305aed65d991a0f55f"),
    "conservative_csv": ("V16E17_R2_Conservative_Evidence_Audit.csv", "785c194aff92d5d3e922fbeb965cafb2d0e2780584c16d677d669ba12602dbe7"),
    "topology_csv": ("V16E17_R2_Diagnostic_Topology_Validation.csv", "20536aaf98c84c516be330c6374c392bf574c15c447ab869ac064e81b70f62b3"),
    "gates_csv": ("V16E17_R2_Final_Gate_Matrix.csv", "9ffef2bdcd10f96252c02d245253759299451a26d43745a5b6cd51e976f738a5"),
}
E17R2_SUCCESS = "V16E17_R2_INDEPENDENT_FULL_GRID_COMPLETION_VALIDATION_PASS"

# -----------------------------------------------------------------------------
# V16E-16 numerical candidate authority.
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

# -----------------------------------------------------------------------------
# Upstream immutable support/background authorities retained in the freeze chain.
# -----------------------------------------------------------------------------
E15_RUNNER = (
    "PAD_Stream_V16E15_SGSim_Unsupported_Cell_Policy_Design_and_Audit.py",
    "a851ec64d85ed019720feffcc4a7f705a100926c8cdf338c934be416f786111c",
)
E15_REL = Path("provenance/hybrid_dp/V16E15_SGSIM_UNSUPPORTED_CELL_POLICY_DESIGN_AUDIT")
E15_CONTRACT = ("V16E15_Unsupported_Cell_Policy_Contract.json", "5c692ea3b9ba4dee0e43005faeee016c4d442f1d8eb24fa7e21651ddc136f5e0")

E14_RUNNER = (
    "PAD_Stream_V16E14_Independent_SGSim_100Day_MapBack_Conservation_and_Support_Audit.py",
    "8225bc3d6e6c5f1731e75b74663285a880206c23c1d82fb524f14cf2122e2898",
)
E14_REL = Path("provenance/hybrid_dp/V16E14_INDEPENDENT_SGSIM_100D_MAPBACK_CONSERVATION_SUPPORT_AUDIT")
E14_SUMMARY = ("PAD_Stream_V16E14_Summary.json", "e57397fc538c374f94c45494df801525c36c0327140ef2fdeb5cab47307d7450")

E13R1_RUNNER = (
    "PAD_Stream_V16E13_R1_Native_Dtype_Identity_Repair_and_Controlled_Conservative_Streamline_to_Grid_MapBack_Execution.py",
    "b8e04c2db9846709c2791afa65d8b10fd9b9e8ada0ac48b0b24cbdf4765e80b6",
)
E13R1_REL = Path("pilots/hybrid_dp/V16E13_R1_SGSIM_100D_CONTROLLED_CONSERVATIVE_MAPBACK")
E13R1_NUMERICAL = ("V16E13_R1_SGSim_100Day_Conservative_MapBack.npz", "6ef79d6f126a96b7e64a5fb7f9d11164758b9c2726657ff4f7874f0e6acfa79f")
E13R1_CONTRACT = ("V16E13_R1_Conservative_MapBack_Contract.json", "733ced4bb7da6b3c808871f36f73634cd5d3da2290cdde3ca099321fb871a048")

E11R2_RUNNER = (
    "PAD_Stream_V16E11_R2_Packed_SG5_Serialization_Repair_and_Controlled_Hybrid_Streamline_Pilot.py",
    "0363a09612c5e80f6bb8124c817ca0d3726b1654283ab169c9b2d4d9861707b7",
)
E11R2_REL = Path("pilots/hybrid_dp/V16E11_R2_SGSIM_100D_CONTROLLED_STREAMLINE_PILOT")
E11R2_PILOT = ("V16E11_R2_SGSim_100Day_Streamline_Pilot.npz", "710720e933d740787868a9894fa04f90e88429c120d9f86a52b750f4c41db844")

# Historical freeze-pattern source authority only. V16 retains its own numerical lineage.
V15_D6 = (
    "PAD_Stream_V15SG7D6_Full_Grid_Candidate_Freeze_Provenance_Manifest.py",
    "5375fcc8bc00d5be19ce8c9f3ca6bd379445e02205c3f593c3f3e5e9571c5e9e",
)

OUT_REL = Path("provenance/hybrid_dp/V16E18_FROZEN_SGSIM_100D_FULL_GRID_CANDIDATE")
BLOCKED_REL = Path("provenance/hybrid_dp/V16E18_BLOCKED_FULL_GRID_CANDIDATE_FREEZE")
FROZEN_SUBDIR = "frozen_full_grid"
FROZEN_NAME = "V16E18_Frozen_SGSim_100Day_Full_Grid_Candidate.npz"

EXPECTED_GRID = (15, 50, 50)
EXPECTED_CELLS = 37500
EXPECTED_SUPPORTED = 20462
EXPECTED_UNSUPPORTED = 17038
EXPECTED_TIME_DAYS = 100.0
EXPECTED_BACKGROUND = 0.2
EXPECTED_FULL_MIN = 0.2
EXPECTED_FULL_MAX = 0.78499960534060065
SELECTED_POLICY = "P4_MASKED_BACKGROUND_PLUS_SUPPORT"

PROHIBITIONS = [
    "NO RE-EXECUTION OF MAP-BACK, BACKGROUND COMPLETION, OR INDEPENDENT RECONSTRUCTION.",
    "NO NUMERICAL VALUE CHANGE; THE V16E-16 CANDIDATE IS COPIED BYTE-FOR-BYTE ONLY.",
    "NO CHANGE TO SUPPORTED-CELL SATURATION OR BACKGROUND-COMPLETED VALUES.",
    "NO CHANGE TO SUPPORT MASK / NUMERATOR / DENOMINATOR / PIECE / VISIT EVIDENCE.",
    "NO INTERPOLATION, NEAREST-NEIGHBOR, ROUTE-SPECIFIC FILL, OR NEW CONSERVATIVE PROJECTION.",
    "NO TRAINING, CHECKPOINT LOAD, OR MODEL INFERENCE.",
    "NO PRESSURE / DARCY / POLLOCK / TOF RECOMPUTATION.",
    "NO SG7E THRESHOLD CREATION OR CHANGE.",
    "NO FULL-GRID PLUME CLAIM; E18 FREEZES THE NUMERICAL DEPLOYMENT INPUT ONLY.",
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
    print("PAD-Stream V16E-18 Full-Grid Candidate Freeze / Provenance Manifest")
    print("=" * 132)
    for line in PROHIBITIONS:
        print(line)

    try:
        # ------------------------------------------------------------------
        # V16E-17-R2 freeze-readiness authority.
        # ------------------------------------------------------------------
        print("\nV16E-17-R2 INDEPENDENT VALIDATION / FREEZE-READINESS AUTHORITY")
        bind(g, "E17R2_runner", root / E17R2_RUNNER[0], E17R2_RUNNER[1])
        e17_paths: dict[str, Path] = {}
        for key, (name, digest) in E17R2.items():
            p = compute / E17R2_REL / name
            bind(g, "E17R2_" + key, p, digest)
            e17_paths[key] = p

        e17_audit = read_json(e17_paths["audit"])
        e17_contract = read_json(e17_paths["contract"])
        e17_ready = read_json(e17_paths["readiness"])
        e17_summary = read_json(e17_paths["summary"])
        e17_gate_rows = read_csv(e17_paths["gates_csv"])

        g.check("E17R2_summary_status_PASS", e17_summary.get("status") == "PASS")
        g.check("E17R2_contract_status_exact", e17_contract.get("status") == E17R2_SUCCESS)
        g.check("E17R2_readiness_status_exact", e17_ready.get("status") == E17R2_SUCCESS)
        g.check("E17R2_audit_status_PASS", e17_audit.get("status") == "PASS")
        g.check("E17R2_all_recorded_gates_pass", len(e17_gate_rows) > 0 and all(csv_bool(r.get("passed")) for r in e17_gate_rows))
        g.check("E17R2_freeze_ready", e17_summary.get("freeze_ready") is True and e17_ready.get("ready_for_V16E18_freeze") is True)
        g.check("E17R2_candidate_not_already_frozen", e17_summary.get("candidate_frozen") is False and e17_ready.get("candidate_frozen") is False)
        g.check("E17R2_full_grid_plume_not_authorized", e17_summary.get("full_grid_plume_authorized") is False and e17_ready.get("full_grid_plume_authorized") is False)
        g.check("E17R2_independent_reconstruction_exact", e17_summary.get("full_grid_reconstruction_exact") is True and e17_audit.get("full_grid_reconstruction_exact") is True)
        g.check("E17R2_independent_reconstruction_L1_zero", float(e17_summary.get("full_grid_reconstruction_L1", np.nan)) == 0.0)
        g.check("E17R2_independent_reconstruction_Linf_zero", float(e17_summary.get("full_grid_reconstruction_Linf", np.nan)) == 0.0)
        g.check("E17R2_support_evidence_exact", e17_summary.get("support_evidence_preserved_exact") is True)
        g.check("E17R2_counts_exact", int(e17_summary.get("supported_cells", -1)) == EXPECTED_SUPPORTED and int(e17_summary.get("unsupported_cells", -1)) == EXPECTED_UNSUPPORTED)
        g.check("E17R2_background_exact", float(e17_summary.get("background_saturation", np.nan)) == EXPECTED_BACKGROUND)
        g.check("E17R2_next_is_E18", str(e17_summary.get("next_milestone", "")).startswith("V16E-18"))

        # ------------------------------------------------------------------
        # V16E-16 candidate source authority.
        # ------------------------------------------------------------------
        print("\nV16E-16 FULL-GRID CANDIDATE SOURCE AUTHORITY")
        bind(g, "E16_runner", root / E16_RUNNER[0], E16_RUNNER[1])
        e16_paths: dict[str, Path] = {}
        for key, (name, digest) in E16.items():
            p = compute / E16_REL / name
            bind(g, "E16_" + key, p, digest)
            e16_paths[key] = p

        e16_contract = read_json(e16_paths["contract"])
        e16_manifest = read_json(e16_paths["manifest"])
        e16_summary = read_json(e16_paths["summary"])
        g.check("E16_contract_status_exact", e16_contract.get("status") == E16_SUCCESS)
        g.check("E16_manifest_status_exact", e16_manifest.get("status") == E16_SUCCESS)
        g.check("E16_summary_status_PASS", e16_summary.get("status") == "PASS")
        g.check("E16_policy_exact", e16_contract.get("selected_policy") == SELECTED_POLICY)
        g.check("E16_candidate_created_not_frozen", e16_summary.get("full_grid_candidate_created") is True and e16_summary.get("candidate_frozen") is False)
        g.check("E16_full_grid_plume_not_authorized", e16_summary.get("full_grid_plume_authorized") is False)
        g.check("E16_candidate_file_hash_manifest_exact", e16_manifest.get("numerical_file_sha256") == E16["numerical"][1])
        g.check("E17R2_candidate_file_identity_exact", e17_ready.get("candidate_file_sha256") == E16["numerical"][1])

        # ------------------------------------------------------------------
        # Upstream support/background/provenance chain.
        # ------------------------------------------------------------------
        print("\nUPSTREAM SUPPORT / BACKGROUND PROVENANCE AUTHORITY")
        bind(g, "E15_runner", root / E15_RUNNER[0], E15_RUNNER[1])
        e15_contract_path = compute / E15_REL / E15_CONTRACT[0]
        bind(g, "E15_contract", e15_contract_path, E15_CONTRACT[1])
        e15_contract = read_json(e15_contract_path)
        g.check("E15_policy_P4", e15_contract.get("selected_policy") == SELECTED_POLICY)
        g.check("E15_background_exact", float(e15_contract.get("background_saturation", np.nan)) == EXPECTED_BACKGROUND)

        bind(g, "E14_runner", root / E14_RUNNER[0], E14_RUNNER[1])
        e14_summary_path = compute / E14_REL / E14_SUMMARY[0]
        bind(g, "E14_summary", e14_summary_path, E14_SUMMARY[1])
        e14_summary = read_json(e14_summary_path)
        g.check("E14_independent_mapback_PASS", e14_summary.get("status") == "PASS" and float(e14_summary.get("state_reconstruction_Linf", np.nan)) == 0.0)

        bind(g, "E13R1_runner", root / E13R1_RUNNER[0], E13R1_RUNNER[1])
        e13_num_path = compute / E13R1_REL / E13R1_NUMERICAL[0]
        e13_contract_path = compute / E13R1_REL / E13R1_CONTRACT[0]
        bind(g, "E13R1_numerical", e13_num_path, E13R1_NUMERICAL[1])
        bind(g, "E13R1_contract", e13_contract_path, E13R1_CONTRACT[1])

        bind(g, "E11R2_runner", root / E11R2_RUNNER[0], E11R2_RUNNER[1])
        pilot_path = compute / E11R2_REL / E11R2_PILOT[0]
        bind(g, "E11R2_pilot", pilot_path, E11R2_PILOT[1])

        # ------------------------------------------------------------------
        # Historical freeze-pattern authority.
        # ------------------------------------------------------------------
        print("\nVERSION-15 FORMAL FREEZE SOURCE AUTHORITY")
        d6_path = root / V15_D6[0]
        bind(g, "V15SG7D6_source", d6_path, V15_D6[1])
        g.check("V15SG7D6_byte_copy_freeze_semantics_present", source_contains(d6_path, [
            "copying the validated SG7D4 artifact byte-for-byte",
            "Frozen full-grid SHA-256 matches validated source",
            "SG7D6 does not modify or regenerate the numerical field",
        ]))

        # ------------------------------------------------------------------
        # Candidate array identity and independent reconstruction replay check.
        # No operation here changes the candidate.
        # ------------------------------------------------------------------
        print("\nFREEZE-ENTRY NUMERICAL IDENTITY")
        with np.load(e16_paths["numerical"], allow_pickle=False) as z16:
            required16 = [
                "saturation_grid_full_float64", "saturation_grid_supported_only_float64",
                "supported_mask", "support_denominator", "support_numerator",
                "segment_piece_count", "streamline_visit_count", "background_saturation",
                "physical_time_days", "grid_shape",
            ]
            g.check("E16_required_freeze_arrays_present", all(k in z16.files for k in required16), str(required16))
            full16 = np.array(z16["saturation_grid_full_float64"], copy=True)
            supported_only16 = np.array(z16["saturation_grid_supported_only_float64"], copy=True)
            mask16 = np.array(z16["supported_mask"], copy=True)
            den16 = np.array(z16["support_denominator"], copy=True)
            num16 = np.array(z16["support_numerator"], copy=True)
            pieces16 = np.array(z16["segment_piece_count"], copy=True)
            visits16 = np.array(z16["streamline_visit_count"], copy=True)
            background16 = float(np.asarray(z16["background_saturation"]))
            time16 = float(np.asarray(z16["physical_time_days"]))
            grid16 = tuple(int(x) for x in np.asarray(z16["grid_shape"]).tolist())

        g.check("candidate_grid_time_exact", full16.shape == EXPECTED_GRID and grid16 == EXPECTED_GRID and time16 == EXPECTED_TIME_DAYS)
        g.check("candidate_full_grid_finite", bool(np.all(np.isfinite(full16))))
        g.check("candidate_cell_count_exact", int(full16.size) == EXPECTED_CELLS)
        g.check("candidate_background_exact", background16 == EXPECTED_BACKGROUND)
        g.check("candidate_bounds_exact", float(np.min(full16)) == EXPECTED_FULL_MIN and float(np.max(full16)) == EXPECTED_FULL_MAX)
        support = np.asarray(mask16, dtype=bool)
        g.check("candidate_support_counts_exact", int(np.sum(support)) == EXPECTED_SUPPORTED and int(np.sum(~support)) == EXPECTED_UNSUPPORTED)
        g.check("candidate_background_completed_cells_remain_unsupported", np.all(den16[~support] == 0.0) and np.all(num16[~support] == 0.0))
        g.check("candidate_array_SHA_matches_E17R2_readiness", arr_sha(full16) == e17_ready.get("candidate_array_sha256"))
        g.check("candidate_support_mask_SHA_matches_E17R2_readiness", arr_sha(mask16) == e17_ready.get("support_mask_array_sha256"))
        g.check("candidate_denominator_SHA_matches_E17R2_readiness", arr_sha(den16) == e17_ready.get("support_denominator_array_sha256"))
        g.check("candidate_numerator_SHA_matches_E17R2_readiness", arr_sha(num16) == e17_ready.get("support_numerator_array_sha256"))

        with np.load(e17_paths["numerical"], allow_pickle=False) as z17:
            required17 = [
                "independently_reconstructed_full_grid_float64", "E16_full_grid_float64",
                "supported_mask", "support_denominator", "support_numerator",
                "segment_piece_count", "streamline_visit_count",
            ]
            g.check("E17R2_required_validation_arrays_present", all(k in z17.files for k in required17), str(required17))
            independent = np.array(z17["independently_reconstructed_full_grid_float64"], copy=True)
            full17 = np.array(z17["E16_full_grid_float64"], copy=True)
            mask17 = np.array(z17["supported_mask"], copy=True)
            den17 = np.array(z17["support_denominator"], copy=True)
            num17 = np.array(z17["support_numerator"], copy=True)
            pieces17 = np.array(z17["segment_piece_count"], copy=True)
            visits17 = np.array(z17["streamline_visit_count"], copy=True)

        g.check("E17R2_independent_full_grid_bitwise_exact_to_E16", np.array_equal(independent, full16) and np.array_equal(full17, full16))
        g.check("E17R2_independent_full_grid_hash_exact_to_E16", arr_sha(independent) == arr_sha(full16) == e17_ready.get("independent_reconstruction_array_sha256"))
        g.check("E17R2_support_provenance_arrays_exact_to_E16", all([
            np.array_equal(mask17, mask16), np.array_equal(den17, den16), np.array_equal(num17, num16),
            np.array_equal(pieces17, pieces16), np.array_equal(visits17, visits16),
        ]))
        g.check("supported_sidecar_shape_exact", supported_only16.shape == EXPECTED_GRID)

        # ------------------------------------------------------------------
        # Formal byte-for-byte freeze. This is the only E18 mutation: creation
        # of a new immutable copy plus provenance metadata. Source is untouched.
        # ------------------------------------------------------------------
        print("\nFORMAL BYTE-FOR-BYTE FREEZE")
        out.mkdir(parents=True, exist_ok=True)
        frozen_dir = out / FROZEN_SUBDIR
        frozen_dir.mkdir(parents=True, exist_ok=True)
        frozen = frozen_dir / FROZEN_NAME
        tmp = frozen.with_suffix(frozen.suffix + ".tmp")
        if tmp.exists():
            tmp.unlink()
        shutil.copyfile(e16_paths["numerical"], tmp)
        os.replace(tmp, frozen)

        source_sha = sha(e16_paths["numerical"])
        frozen_sha = sha(frozen)
        g.check("frozen_file_SHA_exact_source", frozen_sha == source_sha == E16["numerical"][1], frozen_sha)
        g.check("frozen_file_size_exact_source", frozen.stat().st_size == e16_paths["numerical"].stat().st_size)

        with np.load(frozen, allow_pickle=False) as zf:
            frozen_full = np.array(zf["saturation_grid_full_float64"], copy=True)
            frozen_mask = np.array(zf["supported_mask"], copy=True)
            frozen_den = np.array(zf["support_denominator"], copy=True)
            frozen_num = np.array(zf["support_numerator"], copy=True)
            frozen_pieces = np.array(zf["segment_piece_count"], copy=True)
            frozen_visits = np.array(zf["streamline_visit_count"], copy=True)
        g.check("frozen_candidate_array_exact", np.array_equal(frozen_full, full16))
        g.check("frozen_support_provenance_exact", all([
            np.array_equal(frozen_mask, mask16), np.array_equal(frozen_den, den16), np.array_equal(frozen_num, num16),
            np.array_equal(frozen_pieces, pieces16), np.array_equal(frozen_visits, visits16),
        ]))

        # Freeze boundaries / claims.
        g.check("no_numerical_field_regeneration", True)
        g.check("no_mapback_reexecution", True)
        g.check("no_completion_reexecution", True)
        g.check("no_interpolation_or_nearest", True)
        g.check("no_new_conservative_projection", True)
        g.check("SG7E_threshold_unchanged", True)
        g.check("full_grid_plume_not_authorized_in_E18", True)
        g.check("internal_test_OOD_not_reopened", True)

        # ------------------------------------------------------------------
        # Freeze records.
        # ------------------------------------------------------------------
        provenance_chain = [
            {"order": 1, "milestone": "V16E-11-R2", "role": "Frozen 100-day mixed streamline transport", "decision": "1078 frozen streamline states; background constitutive Swc authority retained"},
            {"order": 2, "milestone": "V16E-12-R1", "role": "Map-back protocol freeze", "decision": "Route semantics reconciled; V15-SG7D1 conservative segment/cell operator frozen"},
            {"order": 3, "milestone": "V16E-13-R1", "role": "Conservative supported-cell map-back", "decision": "20,462 supported cells mapped; 17,038 unsupported retained as NaN"},
            {"order": 4, "milestone": "V16E-14", "role": "Independent map-back audit", "decision": "Supported state reconstructed exactly; conservation/support independently validated"},
            {"order": 5, "milestone": "V16E-15", "role": "Unsupported-cell policy design", "decision": "P4 masked background-plus-support selected; constitutive Swc=0.2 authority frozen"},
            {"order": 6, "milestone": "V16E-16", "role": "Controlled full-grid completion", "decision": "17,038 unsupported cells assigned only frozen background; supported state/evidence unchanged"},
            {"order": 7, "milestone": "V16E-17-R2", "role": "Independent full-grid validation", "decision": "Full-grid reconstruction exact; freeze readiness established"},
            {"order": 8, "milestone": "V16E-18", "role": "Formal full-grid freeze", "decision": "Validated E16 candidate copied byte-for-byte and frozen as authoritative 100-day V16 SGSim deployment input"},
        ]

        audit = {
            "milestone": MILESTONE,
            "status": "PASS",
            "freeze_mode": "byte-for-byte copy of independently validated V16E-16 numerical candidate",
            "source_candidate_file": str(e16_paths["numerical"]),
            "source_candidate_sha256": source_sha,
            "frozen_candidate_file": str(frozen),
            "frozen_candidate_sha256": frozen_sha,
            "source_frozen_hash_exact": source_sha == frozen_sha,
            "grid_shape": list(EXPECTED_GRID),
            "physical_time_days": EXPECTED_TIME_DAYS,
            "supported_cells": EXPECTED_SUPPORTED,
            "background_completed_cells": EXPECTED_UNSUPPORTED,
            "background_saturation": EXPECTED_BACKGROUND,
            "full_grid_min": float(np.min(frozen_full)),
            "full_grid_max": float(np.max(frozen_full)),
            "candidate_array_sha256": arr_sha(frozen_full),
            "support_mask_array_sha256": arr_sha(frozen_mask),
            "support_denominator_array_sha256": arr_sha(frozen_den),
            "support_numerator_array_sha256": arr_sha(frozen_num),
            "segment_piece_count_array_sha256": arr_sha(frozen_pieces),
            "streamline_visit_count_array_sha256": arr_sha(frozen_visits),
            "numerical_field_changed": False,
            "support_provenance_changed": False,
            "candidate_frozen": True,
            "full_grid_plume_authorized": False,
            "SG7E_threshold_changed": False,
            "next_milestone": NEXT_PASS,
        }

        freeze_manifest = {
            "milestone": MILESTONE,
            "status": SUCCESS,
            "candidate": "V16E16_background_completed_full_grid_float64",
            "candidate_frozen": True,
            "authoritative_frozen_file": str(frozen),
            "authoritative_frozen_sha256": frozen_sha,
            "source_candidate_file": E16["numerical"][0],
            "source_candidate_sha256": source_sha,
            "source_candidate_array_sha256": arr_sha(full16),
            "independent_validation_milestone": "V16E-17-R2",
            "independent_validation_numerical_sha256": E17R2["numerical"][1],
            "independent_reconstruction_array_sha256": arr_sha(independent),
            "independent_reconstruction_exact": True,
            "grid_shape": list(EXPECTED_GRID),
            "physical_time_days": EXPECTED_TIME_DAYS,
            "supported_cells": EXPECTED_SUPPORTED,
            "background_completed_cells": EXPECTED_UNSUPPORTED,
            "background_saturation": EXPECTED_BACKGROUND,
            "selected_policy": SELECTED_POLICY,
            "support_mask_array_sha256": arr_sha(mask16),
            "support_denominator_array_sha256": arr_sha(den16),
            "support_numerator_array_sha256": arr_sha(num16),
            "segment_piece_count_array_sha256": arr_sha(pieces16),
            "streamline_visit_count_array_sha256": arr_sha(visits16),
            "numerical_field_changed": False,
            "support_provenance_changed": False,
            "full_grid_plume_authorized": False,
            "SG7E_threshold_changed": False,
            "next_milestone": NEXT_PASS,
        }

        deployment_contract = {
            "contract_name": "PAD-Stream V16E-18 Frozen SGSim 100-Day Full-Grid Deployment Contract",
            "freeze_milestone": MILESTONE,
            "status": SUCCESS,
            "candidate": "V16E16_background_completed_full_grid_float64",
            "authoritative_artifact": str(frozen),
            "authoritative_sha256": frozen_sha,
            "grid_shape": list(EXPECTED_GRID),
            "physical_time_days": EXPECTED_TIME_DAYS,
            "transport_source": "V16E-11-R2 frozen mixed Hybrid/R2/SG7A streamline state",
            "mapback_source": "V16E-13-R1 V15-SG7D1 segment/cell conservative map-back",
            "unsupported_cell_policy": SELECTED_POLICY,
            "background_authority": "V16E-11-R2 constitutive_swc",
            "background_saturation": EXPECTED_BACKGROUND,
            "support_provenance": {
                "supported_cells": EXPECTED_SUPPORTED,
                "background_completed_cells": EXPECTED_UNSUPPORTED,
                "background_completed_cells_remain_unsupported": True,
                "support_mask_immutable": True,
                "support_denominator_immutable": True,
                "support_numerator_immutable": True,
                "segment_piece_count_immutable": True,
                "streamline_visit_count_immutable": True,
            },
            "invariants": {
                "frozen_candidate_bytes_immutable": True,
                "supported_state_immutable": True,
                "background_completion_rule_immutable": True,
                "interpolation_prohibited": True,
                "nearest_neighbor_prohibited": True,
                "route_specific_fill_prohibited": True,
                "new_conservative_projection_prohibited": True,
                "SG7E_threshold_not_defined_or_changed_by_E18": True,
                "full_grid_plume_claim_not_authorized_by_E18": True,
            },
            "downstream_use": "Authoritative 100-day full-grid saturation input for V16E-19 deployment validation/baseline audit only.",
            "next_milestone": NEXT_PASS,
        }

        source_authority = {
            "E17R2_runner_sha256": E17R2_RUNNER[1],
            "E17R2_artifacts": {k: {"file": v[0], "sha256": v[1]} for k, v in E17R2.items()},
            "E16_runner_sha256": E16_RUNNER[1],
            "E16_artifacts": {k: {"file": v[0], "sha256": v[1]} for k, v in E16.items()},
            "E15_runner_sha256": E15_RUNNER[1],
            "E15_contract_sha256": E15_CONTRACT[1],
            "E14_runner_sha256": E14_RUNNER[1],
            "E14_summary_sha256": E14_SUMMARY[1],
            "E13R1_runner_sha256": E13R1_RUNNER[1],
            "E13R1_numerical_sha256": E13R1_NUMERICAL[1],
            "E13R1_contract_sha256": E13R1_CONTRACT[1],
            "E11R2_runner_sha256": E11R2_RUNNER[1],
            "E11R2_pilot_sha256": E11R2_PILOT[1],
            "V15SG7D6_source_sha256": V15_D6[1],
        }
        freeze_manifest["source_authority"] = source_authority
        deployment_contract["source_authority"] = source_authority
        audit["source_authority"] = source_authority

        summary = {
            "milestone": MILESTONE,
            "status": "PASS",
            "candidate": "V16E16_background_completed_full_grid_float64",
            "candidate_frozen": True,
            "frozen_full_grid_sha256": frozen_sha,
            "source_frozen_hash_exact": True,
            "grid_shape": list(EXPECTED_GRID),
            "physical_time_days": EXPECTED_TIME_DAYS,
            "supported_cells": EXPECTED_SUPPORTED,
            "background_completed_cells": EXPECTED_UNSUPPORTED,
            "background_saturation": EXPECTED_BACKGROUND,
            "full_grid_min": float(np.min(frozen_full)),
            "full_grid_max": float(np.max(frozen_full)),
            "independent_validation_exact": True,
            "support_evidence_preserved_exact": True,
            "numerical_field_changed": False,
            "support_provenance_changed": False,
            "full_grid_plume_authorized": False,
            "SG7E_threshold_changed": False,
            "internal_test_reopened": False,
            "OOD_reopened": False,
            "next_milestone": NEXT_PASS,
        }

        handoff = f"""# PAD-Stream V16E-18 - Full-Grid Candidate Freeze / Provenance Manifest PASS

The independently validated V16E-16 100-day SGSim full-grid candidate is now formally frozen byte-for-byte.

- Grid: 15 x 50 x 50
- Physical time: {EXPECTED_TIME_DAYS:.1f} days
- Supported cells retained from conservative map-back: {EXPECTED_SUPPORTED}
- Background-completed cells: {EXPECTED_UNSUPPORTED}
- Frozen constitutive background Swc: {EXPECTED_BACKGROUND:.17g}
- Source candidate SHA-256: {source_sha}
- Frozen candidate SHA-256: {frozen_sha}
- Source/frozen byte identity: YES
- Independent V16E-17-R2 reconstruction exact: YES
- Support mask / numerator / denominator / piece / visit evidence: immutable
- Numerical field changed by E18: NO
- Candidate frozen: YES
- Full-grid plume authorized: NO
- SG7E threshold changed or created: NO

NEXT: {NEXT_PASS}
""".encode("utf-8")

        files = {
            "V16E18_Full_Grid_Freeze_Audit.json": enc(audit),
            "V16E18_Full_Grid_Freeze_Manifest.json": enc(freeze_manifest),
            "V16E18_Frozen_Grid_Deployment_Contract.json": enc(deployment_contract),
            "PAD_Stream_V16E18_Summary.json": enc(summary),
            "V16E18_Handoff.md": handoff,
        }
        for name, data in files.items():
            atomic_write(out / name, data)

        artifact_rows = []
        for role, path in [
            ("V16E17-R2 independent validation", e17_paths["numerical"]),
            ("V16E16 source full-grid candidate", e16_paths["numerical"]),
            ("V16E13-R1 conservative map-back", e13_num_path),
            ("V16E11-R2 frozen streamline pilot", pilot_path),
            ("V16E18 frozen full-grid candidate", frozen),
        ]:
            artifact_rows.append({"role": role, "path": str(path), "sha256": sha(path), "size_bytes": path.stat().st_size})
        save_csv(out / "V16E18_Artifact_Hashes.csv", artifact_rows)

        save_csv(out / "V16E18_Provenance_Chain.csv", provenance_chain)
        save_csv(out / "V16E18_Frozen_Gate_Record.csv", [
            {"gate": name, "passed": rec["passed"], "detail": rec["detail"], "frozen_by": MILESTONE}
            for name, rec in g.items.items()
        ])
        save_csv(out / "V16E18_Frozen_Full_Grid_Identity.csv", [{
            "candidate": "V16E16_background_completed_full_grid_float64",
            "freeze_milestone": MILESTONE,
            "source_validation_milestone": "V16E-17-R2",
            "frozen_file": str(frozen),
            "frozen_sha256": frozen_sha,
            "source_sha256": source_sha,
            "grid_shape": "15x50x50",
            "physical_time_days": EXPECTED_TIME_DAYS,
            "supported_cells": EXPECTED_SUPPORTED,
            "background_completed_cells": EXPECTED_UNSUPPORTED,
            "background_saturation": EXPECTED_BACKGROUND,
            "grid_min": float(np.min(frozen_full)),
            "grid_max": float(np.max(frozen_full)),
            "support_mask_preserved": True,
            "support_denominator_preserved": True,
            "support_numerator_preserved": True,
            "segment_piece_count_preserved": True,
            "streamline_visit_count_preserved": True,
            "independent_reconstruction_exact": True,
            "full_grid_plume_authorized": False,
        }])

        print("\n" + "=" * 132)
        print("V16E-18 RESULT: PASS")
        print("=" * 132)
        print(f"{'SGSim grid':72}: 15 x 50 x 50")
        print(f"{'Physical time':72}: {EXPECTED_TIME_DAYS:.1f} days")
        print(f"{'Supported cells':72}: {EXPECTED_SUPPORTED}")
        print(f"{'Background-completed cells':72}: {EXPECTED_UNSUPPORTED}")
        print(f"{'Frozen background saturation Swc':72}: {EXPECTED_BACKGROUND:.17g}")
        print(f"{'Independent validation exact':72}: YES")
        print(f"{'Frozen candidate source/frozen SHA exact':72}: YES")
        print(f"{'Frozen candidate SHA-256':72}: {frozen_sha}")
        print(f"{'Numerical field changed by E18':72}: NO")
        print(f"{'Support/conservative evidence preserved':72}: YES")
        print(f"{'Candidate frozen':72}: YES")
        print(f"{'Full-grid plume authorized':72}: NO")
        print(f"{'SG7E threshold changed/created':72}: NO")
        print(f"{'Internal test / OOD reopened':72}: NO / NO")
        for name in files:
            print(f"{name} SHA: {sha(out / name)}")
        for name in [
            "V16E18_Artifact_Hashes.csv",
            "V16E18_Provenance_Chain.csv",
            "V16E18_Frozen_Gate_Record.csv",
            "V16E18_Frozen_Full_Grid_Identity.csv",
        ]:
            print(f"{name} SHA: {sha(out / name)}")
        print("Output:", out)
        print("Frozen candidate:", frozen)
        print("NEXT:", NEXT_PASS)
        return 0

    except Exception as exc:
        print(f"\n[FAIL] V16E-18 did not close: {exc}", flush=True)
        try:
            blocked.mkdir(parents=True, exist_ok=True)
            report = {
                "milestone": MILESTONE,
                "status": BLOCKED,
                "exception": repr(exc),
                "gates": g.items,
                "E17R2_modified": False,
                "E16_modified": False,
                "E15_modified": False,
                "E14_modified": False,
                "E13R1_modified": False,
                "E11R2_modified": False,
                "candidate_frozen": False,
                "full_grid_plume_authorized": False,
                "SG7E_threshold_changed": False,
                "next_milestone": NEXT_FAIL,
            }
            p = blocked / "V16E18_Blocked_Full_Grid_Candidate_Freeze_Audit.json"
            atomic_write(p, enc(report))
            print("Blocked report SHA:", sha(p))
            print("Blocked output:", blocked)
        except Exception:
            pass
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
