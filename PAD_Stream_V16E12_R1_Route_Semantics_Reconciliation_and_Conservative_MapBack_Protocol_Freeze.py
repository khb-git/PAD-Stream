#!/usr/bin/env python3
"""PAD-Stream V16E-12-R1
SGSim 100-Day Streamline Pilot Evidence Freeze and Conservative Map-Back Protocol.

Purpose
-------
Freeze the successful V16E-11-R2 mixed learned/exact 100-day streamline state
and define the only authorized first conservative streamline-to-grid map-back
operator for the SGSim dissertation base.

This revision performs NO map-back.  It binds the exact E11-R2 pilot and the
accepted Version-15 SG7D0/SG7D1/SG7D2 map-back lineage, and repairs only the blocked route-label interpretation, then freezes an adapter
contract for the next execution milestone.

Scientific boundary
-------------------
- E11-R2 saturation_100d is immutable map-back transport state.
- Route labels are provenance only; there is one common map-back operator.
- Geometry is the frozen SG6 201-node Pollock path geometry from E11-R2.
- Streamline flux weights remain frozen.
- V15 SG7D1 piecewise-linear segment/cell intersection accumulation is the
  map-back operator authority.
- First execution leaves unsupported cells NaN; no fill/interpolation.
- No SG7E/full-grid plume claim is authorized by this protocol freeze.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any

import numpy as np

MILESTONE = "V16E-12-R1"
SUCCESS = "V16E12_R1_ROUTE_SEMANTICS_RECONCILED_PILOT_EVIDENCE_AND_MAPBACK_PROTOCOL_FREEZE_PASS"
BLOCKED = "V16E12_R1_ROUTE_SEMANTICS_RECONCILIATION_OR_MAPBACK_PROTOCOL_FREEZE_BLOCKED"
NEXT_PASS = "V16E-13 — SGSim 100-Day Controlled Conservative Streamline-to-Grid Map-Back Execution"
NEXT_FAIL = "V16E-12-R2 — Repair only the newly failed evidence/protocol gate; map-back remains locked"

E11R2_RUNNER = (
    "PAD_Stream_V16E11_R2_Packed_SG5_Serialization_Repair_and_Controlled_Hybrid_Streamline_Pilot.py",
    "0363a09612c5e80f6bb8124c817ca0d3726b1654283ab169c9b2d4d9861707b7",
)
E11R2_RECOVERY_RUNNER = (
    "PAD_Stream_V16E11_R2_Packed_SG5_Artifact_Recovery_and_Rebind.py",
    "491f3d1e8c5ef3b576a503abd3d1e84160b986d7fa1bacca55388f647153e498",
)
E11R2_REL = Path("pilots/hybrid_dp/V16E11_R2_SGSIM_100D_CONTROLLED_STREAMLINE_PILOT")
E11R2 = {
    "pilot": ("V16E11_R2_SGSim_100Day_Streamline_Pilot.npz", "710720e933d740787868a9894fa04f90e88429c120d9f86a52b750f4c41db844"),
    "audit": ("V16E11_R2_Path_Eligibility_and_Screening_Audit.json", "170dde9c74b26f949ef90de3d67001a124e740822fe587c032ae2f066379df4f"),
    "summary": ("PAD_Stream_V16E11_R2_Summary.json", "76336276daf4a506ea7e0880a6ad2e2852724deaf4623ca3945eafbf029e4243"),
    "handoff": ("V16E11_R2_Handoff.md", "d0eb4f3da3741ea5db96420652f6f9ebd76a1684d3efa400fa4a2db3d8f4aa11"),
}
E11R2_RECOVERY_REL = Path("provenance/hybrid_dp/V16E11_R2_PACKED_SG5_ARTIFACT_RECOVERY")
E11R2_RECOVERY = {
    "audit": ("V16E11_R2_Frozen_SGSim_Artifact_Recovery_Audit.json", "6bd78f1f38b333edb60115ef7ba02845533f155796f62fd4d22160122d3d1ceb"),
    "summary": ("PAD_Stream_V16E11_R2_Recovery_Summary.json", "a766e302133bb45c27fb4bcd13964e9ffad3a2ce43063830c9b1a18d32c709a5"),
    "handoff": ("V16E11_R2_Recovery_Handoff.md", "1f858eb3efb4031afa0502cb4b5ecb79a44f8a9aedd8407a9321bfa872f3b7d7"),
}


# Immutable blocked V16E-12 evidence.  R1 is a revision, never an in-place edit.
E12_PARENT_RUNNER = (
    "PAD_Stream_V16E12_SGSim_100Day_Streamline_Pilot_Evidence_Freeze_and_Conservative_MapBack_Protocol.py",
    "67d3daed6d88b1546f3133c814fffded63e3a5b1a3356da40561b0e04fc5aeea",
)
E12_BLOCKED_REL = Path("provenance/hybrid_dp/V16E12_BLOCKED_EVIDENCE_OR_MAPBACK_PROTOCOL")
E12_BLOCKED_AUDIT = (
    "V16E12_Blocked_Audit.json",
    "69b74060cb5c38b7b2c54451ba4cb0d52b6922a6dd873fdfded6829266080c03",
)

# Version-15 map-back lineage. E12 freezes the exact repository SHAs observed at
# runtime into its output contract; E13 must bind those E12-recorded identities.
MAPBACK_SOURCES = [
    "PAD_Stream_V15SG7D0_Frozen_L2_MapBack_Contract_Data_Interface_Audit.py",
    "PAD_Stream_V15SG7D1_Conservative_Frozen_L2_Streamline_to_Grid_MapBack.py",
    "PAD_Stream_V15SG7D2_Independent_MapBack_Conservation_Support_Audit.py",
]

OUT_REL = Path("provenance/hybrid_dp/V16E12_R1_ROUTE_SEMANTICS_RECONCILED_PILOT_EVIDENCE_AND_MAPBACK_PROTOCOL_FREEZE")

EXPECTED_NSTREAM = 1078
EXPECTED_NXI = 201
GRID_SHAPE = (15, 50, 50)
DX_FT, DY_FT, DZ_FT = 20.0, 20.0, 4.0
FT_TO_M = 0.3048
CELL_SIZE_M = (DZ_FT * FT_TO_M, DY_FT * FT_TO_M, DX_FT * FT_TO_M)  # k,j,i convention
EXPECTED_ROUTE_COUNTS = {
    "HYBRID10_ACCEPT": 462,
    "HYBRID12_ACCEPT": 0,
    "EXACT_R2_FALLBACK": 41,
    "FULL_PHYSICS_SG7A_FALLBACK": 575,
}
EXPECTED_ROUTE_CODES = {
    "HYBRID10_ACCEPT": 10,
    "HYBRID12_ACCEPT": 12,
    "EXACT_R2_FALLBACK": 20,
    "FULL_PHYSICS_SG7A_FALLBACK": 30,
    "BLOCKED_UNRESOLVED": 99,
}

# E11-R2 deliberately stores a coarse execution class in route_code and a
# more specific provenance subtype in route_label.  The blocked E12 runner
# incorrectly required route_label to equal the coarse class name.
EXPECTED_DETAILED_ROUTE_LABEL_COUNTS = {
    "HYBRID10_ACCEPT": 462,
    "EXACT_R2_FALLBACK_CLOCK": 41,
    "FULL_PHYSICS_SG7A_POSTBT": 575,
}
DETAILED_LABEL_TO_CODE = {
    "HYBRID10_ACCEPT": 10,
    "HYBRID12_ACCEPT": 12,
    "EXACT_R2_FALLBACK_CLOCK": 20,
    "EXACT_R2_FALLBACK_SCREEN": 20,
    "FULL_PHYSICS_SG7A_POSTBT": 30,
    "BLOCKED_UNRESOLVED": 99,
}

PROHIBITIONS = [
    "NO TRAINING OR GRADIENT UPDATE.",
    "NO CHECKPOINT LOAD OR MODEL INFERENCE.",
    "NO PRESSURE / DARCY / POLLOCK / TOF RECOMPUTATION.",
    "NO CHANGE TO E11-R2 STREAMLINE SATURATION, ROUTES, OR FALLBACKS.",
    "NO CHANGE TO E11-R2 ROUTE CODES OR DETAILED ROUTE LABELS; ONLY THEIR E12 INTERPRETATION IS REPAIRED.",
    "NO STREAMLINE-TO-GRID MAP-BACK EXECUTION IN E12.",
    "NO ROUTE-SPECIFIC GRID OPERATOR; ROUTE LABELS ARE PROVENANCE ONLY.",
    "NO NODE-ONLY OR NEAREST-CELL DEPOSITION SUBSTITUTE FOR V15 SG7D1.",
    "NO UNSUPPORTED-CELL FILL, INTERPOLATION, OR BACKGROUND COMPLETION.",
    "NO GLOBAL FULL-GRID CONSERVATIVE PROJECTION IN E12/E13 FIRST PASS.",
    "NO SG7E THRESHOLDING OR FULL-GRID PLUME CLAIM.",
    "NO INTERNAL-TEST REOPENING OR OOD REOPENING.",
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
    if isinstance(v, dict): return {str(k): native(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)): return [native(x) for x in v]
    if isinstance(v, np.ndarray): return native(v.tolist())
    if isinstance(v, np.generic): return v.item()
    if isinstance(v, Path): return str(v)
    return v

def enc(v: Any) -> bytes:
    return (json.dumps(native(v), indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")

def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def bind(g: Gates, label: str, path: Path, expected: str):
    g.check(label + "_exists", path.is_file(), str(path))
    actual = sha(path)
    g.check(label + "_SHA_exact", actual == expected, actual if actual != expected else "")
    return actual

def source_semantics(text: str) -> dict[str, bool]:
    low = text.lower()
    def has(*terms): return all(t.lower() in low for t in terms)
    return {
        "piecewise_linear_segments": has("piecewise-linear streamline segments"),
        "clip_segment_to_box": has("clip_segment_to_box"),
        "split_at_cell_boundaries": has("split_segment_by_cell_boundaries"),
        "flow_weighted_segment_length": has("measure = wm * dl"),
        "linear_saturation_midpoint": has("smid = s0 + t_mid * (s1 - s0)"),
        "cell_weighted_average": has("numerator[k, jj, i] += measure * smid", "denominator[k, jj, i] += measure"),
        "unsupported_nan": has("explicit_nan_no_fill") or has("unsupported cells remain explicit"),
        "closure_1e8": has("support_closure_rel <= 1e-8", "sat_measure_closure_rel <= 1e-8"),
    }

def publish(out: Path, files: dict[str, bytes]):
    out.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        p = out / name
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_bytes(data)
        os.replace(tmp, p)

def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=str(Path(__file__).resolve().parent))
    ap.add_argument("--compute-root", default="/content/drive/MyDrive/PAD_Stream_Compute")
    args = ap.parse_args()
    repo = Path(args.repo_root).resolve()
    compute = Path(args.compute_root).resolve()
    out = compute / OUT_REL
    g = Gates()

    print("=" * 126)
    print("PAD-Stream V16E-12-R1 Route-Semantics Reconciliation, Pilot Evidence Freeze, and Conservative Map-Back Protocol")
    print("=" * 126)
    for line in PROHIBITIONS: print(line)

    try:
        print("\nBLOCKED V16E-12 PARENT EVIDENCE")
        bind(g, "E12_parent_runner", repo / E12_PARENT_RUNNER[0], E12_PARENT_RUNNER[1])
        e12_blocked_path = compute / E12_BLOCKED_REL / E12_BLOCKED_AUDIT[0]
        bind(g, "E12_blocked_audit", e12_blocked_path, E12_BLOCKED_AUDIT[1])
        e12_blocked = read_json(e12_blocked_path)
        g.check("E12_parent_status_BLOCKED", "BLOCKED" in str(e12_blocked.get("status","")).upper())
        g.check("E12_parent_failed_only_before_mapback", e12_blocked.get("mapback_performed") is False)
        g.check("E12_parent_full_grid_not_authorized", e12_blocked.get("full_grid_plume_authorized") is False)
        g.check("E12_parent_route_label_gate_identified",
                "pilot_route_counts_exact" in str(e12_blocked.get("exception","")))
        parent_gates = e12_blocked.get("gates", {})
        g.check("E12_parent_all_prior_pilot_gates_passed",
                all(bool(v.get("passed")) for k,v in parent_gates.items()
                    if k != "pilot_route_counts_exact"))
        g.check("E12_parent_route_count_gate_failed",
                parent_gates.get("pilot_route_counts_exact",{}).get("passed") is False)

        print("\nV16E-11-R2 PILOT AUTHORITY")
        bind(g, "E11R2_runner", repo / E11R2_RUNNER[0], E11R2_RUNNER[1])
        bind(g, "E11R2_recovery_runner", repo / E11R2_RECOVERY_RUNNER[0], E11R2_RECOVERY_RUNNER[1])
        pilot_paths = {}
        for k, (fn, hs) in E11R2.items():
            p = compute / E11R2_REL / fn
            bind(g, "E11R2_" + k, p, hs)
            pilot_paths[k] = p

        # Recovery provenance is bound when present. It is required for E12 because
        # the recovered workspace is part of the evidence chain that made E11-R2 executable.
        recovery_paths = {}
        for k, (fn, hs) in E11R2_RECOVERY.items():
            p = compute / E11R2_RECOVERY_REL / fn
            bind(g, "E11R2_recovery_" + k, p, hs)
            recovery_paths[k] = p

        summary = read_json(pilot_paths["summary"])
        audit = read_json(pilot_paths["audit"])
        g.check("E11R2_status_PASS", summary.get("status") == "PASS")
        g.check("E11R2_streamline_count_exact", int(summary.get("streamline_count", -1)) == EXPECTED_NSTREAM)
        g.check("E11R2_transport_nodes_exact", int(summary.get("transport_nodes", -1)) == EXPECTED_NXI)
        g.check("E11R2_physical_time_100d", float(summary.get("physical_time_days", -1)) == 100.0)
        g.check("E11R2_zero_unsafe", int(summary.get("unsafe_learned_proposals_accepted", -1)) == 0)
        g.check("E11R2_no_mapback", summary.get("grid_mapback_performed") is False)
        g.check("E11R2_no_test_OOD", summary.get("internal_test_reopened") is False and summary.get("OOD_opened") is False)

        print("\nE11-R2 NUMERICAL PILOT EVIDENCE")
        with np.load(pilot_paths["pilot"], allow_pickle=False) as z:
            required = [
                "physical_time_days","xi","xyz_m","tau_s","tau_end_s","weights_m3_s","producer","streamline_id",
                "exact_cell_kji","tD_100","xD_star_100","Sw_star","characteristic_speed","route_code","route_label",
                "learned_screen_pass","learned_screen_reasons","saturation_100d",
                "constitutive_no","constitutive_nw","constitutive_swc","constitutive_sor","constitutive_mu_w_cP",
                "constitutive_mu_o_cP","constitutive_phi","constitutive_krw_max","constitutive_kro_max",
            ]
            g.check("pilot_required_keys_exact_subset", all(k in z.files for k in required), str(z.files))
            xi = np.asarray(z["xi"])
            xyz = np.asarray(z["xyz_m"])
            tau = np.asarray(z["tau_s"])
            tau_end = np.asarray(z["tau_end_s"])
            weights = np.asarray(z["weights_m3_s"])
            cells = np.asarray(z["exact_cell_kji"])
            routes = np.asarray(z["route_label"]).astype(str)
            route_codes = np.asarray(z["route_code"])
            sat = np.asarray(z["saturation_100d"])
            g.check("pilot_xi_201", xi.shape == (EXPECTED_NXI,) and np.array_equal(xi, np.linspace(0.0,1.0,EXPECTED_NXI)))
            g.check("pilot_xyz_shape", xyz.shape == (EXPECTED_NSTREAM,EXPECTED_NXI,3))
            g.check("pilot_tau_shape", tau.shape == (EXPECTED_NSTREAM,EXPECTED_NXI))
            g.check("pilot_tau_end_shape", tau_end.shape == (EXPECTED_NSTREAM,))
            g.check("pilot_weights_shape_positive", weights.shape == (EXPECTED_NSTREAM,) and np.all(np.isfinite(weights)) and np.all(weights > 0))
            g.check("pilot_exact_cells_shape", cells.shape == (EXPECTED_NSTREAM,EXPECTED_NXI,3))
            g.check("pilot_saturation_shape_finite", sat.shape == (EXPECTED_NSTREAM,EXPECTED_NXI) and np.all(np.isfinite(sat)))
            swc = float(np.asarray(z["constitutive_swc"]).item()); sor = float(np.asarray(z["constitutive_sor"]).item())
            g.check("pilot_saturation_physical_bounds", np.all(sat >= swc-1e-7) and np.all(sat <= 1.0-sor+1e-7))
            g.check("pilot_tau_monotonic_and_end_match", np.all(np.diff(tau,axis=1) >= -1e-12) and np.allclose(tau[:,-1],tau_end,rtol=1e-12,atol=1e-9))
            # R1 repair: route_code is the canonical coarse execution class.
            # route_label is a detailed provenance subtype and must not be
            # counted as though it were the coarse class name.
            observed = {
                label: int(np.sum(route_codes == code))
                for label, code in EXPECTED_ROUTE_CODES.items()
                if label != "BLOCKED_UNRESOLVED"
            }
            g.check("pilot_route_class_counts_from_code_exact",
                    observed == EXPECTED_ROUTE_COUNTS,
                    json.dumps(observed, sort_keys=True))
            g.check("pilot_no_blocked_route",
                    int(np.sum(route_codes == EXPECTED_ROUTE_CODES["BLOCKED_UNRESOLVED"])) == 0)
            g.check("pilot_Hybrid12_unused", observed["HYBRID12_ACCEPT"] == 0)
            g.check("pilot_Hybrid10_462", observed["HYBRID10_ACCEPT"] == 462)
            g.check("pilot_R2_41", observed["EXACT_R2_FALLBACK"] == 41)
            g.check("pilot_SG7A_575", observed["FULL_PHYSICS_SG7A_FALLBACK"] == 575)

            detailed_observed = {
                label: int(np.sum(routes == label))
                for label in sorted(set(routes.tolist()))
            }
            g.check("pilot_detailed_route_labels_exact",
                    detailed_observed == EXPECTED_DETAILED_ROUTE_LABEL_COUNTS,
                    json.dumps(detailed_observed, sort_keys=True))
            g.check("pilot_all_detailed_labels_known",
                    set(detailed_observed).issubset(DETAILED_LABEL_TO_CODE))
            g.check("pilot_detailed_label_to_code_consistency",
                    all(np.all(route_codes[routes == label] == DETAILED_LABEL_TO_CODE[label])
                        for label in detailed_observed))
            g.check("pilot_route_semantics_reconciled_without_data_change",
                    sum(observed.values()) == EXPECTED_NSTREAM
                    and sum(detailed_observed.values()) == EXPECTED_NSTREAM)
            # Freeze hashes of numerical arrays independent of NPZ compression/container metadata.
            array_hashes = {}
            for k in ["xi","xyz_m","tau_s","tau_end_s","weights_m3_s","exact_cell_kji","route_code","route_label","saturation_100d"]:
                a = np.ascontiguousarray(np.asarray(z[k]))
                array_hashes[k] = hashlib.sha256(a.tobytes()).hexdigest()

        print("\nVERSION-15 CONSERVATIVE MAP-BACK AUTHORITY")
        source_records = {}
        for fn in MAPBACK_SOURCES:
            p = repo / fn
            g.check("source_" + fn.replace('.','_') + "_exists", p.is_file(), str(p))
            text = p.read_text(encoding="utf-8", errors="replace")
            source_records[fn] = {"sha256":sha(p),"semantics":source_semantics(text)}
        d1 = source_records[MAPBACK_SOURCES[1]]["semantics"]
        for name, val in d1.items(): g.check("V15SG7D1_"+name, val)
        d2_text = (repo / MAPBACK_SOURCES[2]).read_text(encoding="utf-8", errors="replace").lower()
        g.check("V15SG7D2_independent_audit_requires_nan_unsupported", "unsupported cells remain nan" in d2_text)
        g.check("V15SG7D2_independent_closure_1e8", ("support_closure_limit = 1e-8" in d2_text or "support_closure_limit = 1.0e-8" in d2_text) and ("sat_measure_closure_limit = 1e-8" in d2_text or "sat_measure_closure_limit = 1.0e-8" in d2_text))

        print("\nV16E-12-R1 CONSERVATIVE MAP-BACK PROTOCOL")
        protocol = {
            "milestone": MILESTONE,
            "status": SUCCESS,
            "parent_evidence": {
                "blocked_E12_runner_sha256": E12_PARENT_RUNNER[1],
                "blocked_E12_audit_sha256": E12_BLOCKED_AUDIT[1],
                "E11R2_pilot_npz_sha256": E11R2["pilot"][1],
                "E11R2_audit_sha256": E11R2["audit"][1],
                "E11R2_summary_sha256": E11R2["summary"][1],
                "E11R2_handoff_sha256": E11R2["handoff"][1],
                "route_counts": EXPECTED_ROUTE_COUNTS,
                "detailed_route_label_counts": EXPECTED_DETAILED_ROUTE_LABEL_COUNTS,
                "route_semantics": "route_code=canonical coarse execution class; route_label=detailed provenance subtype",
                "unsafe_learned_proposals_accepted": 0,
                "pilot_array_sha256": array_hashes,
            },
            "frozen_mapback_source_lineage": source_records,
            "mapback_input_contract": {
                "saturation_state_key": "saturation_100d",
                "saturation_state_immutable": True,
                "geometry_key": "xyz_m",
                "flow_weight_key": "weights_m3_s",
                "exact_cell_key": "exact_cell_kji",
                "exact_cell_role": "audit/topology sidecar; not a replacement for segment/cell intersection deposition",
                "route_code_role": "canonical coarse execution class used for class counts",
                "route_label_role": "detailed provenance subtype only; no route-specific map-back operator",
                "streamlines": EXPECTED_NSTREAM,
                "nodes_per_streamline": EXPECTED_NXI,
                "physical_time_days": 100.0,
            },
            "grid_contract": {
                "shape_kji": list(GRID_SHAPE),
                "cell_size_ft_xyz": [DX_FT,DY_FT,DZ_FT],
                "cell_size_m_xyz": [DX_FT*FT_TO_M,DY_FT*FT_TO_M,DZ_FT*FT_TO_M],
                "array_order": "(k,j,i)=(z,y,x)",
            },
            "operator_contract": {
                "authority": "V15-SG7D1",
                "method": "flow-weighted piecewise-linear segment/cell intersection accumulation",
                "segment_handling": "clip to Cartesian reservoir box, split exactly at cell-boundary crossings",
                "saturation_on_segment": "linear interpolation between adjacent 201-node saturation samples; evaluate at each deposited subsegment midpoint",
                "deposition_measure": "streamline_weight_m3_s * subsegment_length_m",
                "cell_numerator": "sum(weight * dl * S_mid)",
                "cell_denominator": "sum(weight * dl)",
                "supported_cell_saturation": "numerator / denominator",
                "unsupported_cell_state": "NaN",
                "unsupported_fill_authorized": False,
                "global_full_grid_projection_authorized": False,
                "support_closure_relative_max": 1.0e-8,
                "saturation_measure_closure_relative_max": 1.0e-8,
                "mapped_bounds": [swc,1.0-sor],
                "deterministic_repeat_required": True,
            },
            "execution_firewall": {
                "training": False,
                "model_inference": False,
                "pressure_Darcy_Pollock_TOF_recompute": False,
                "transport_state_change": False,
                "unsupported_cell_fill": False,
                "SG7E_thresholding": False,
                "internal_test_reopen": False,
                "OOD_reopen": False,
            },
            "E13_authorization": "Execute only the frozen operator above on the exact E11-R2 pilot; publish a supported-cell grid with unsupported cells NaN. Do not fill unsupported cells.",
            "post_E13_required_audit": "Independent V16 map-back conservation/support audit before any unsupported-cell policy or full-grid plume claim.",
            "next_milestone": NEXT_PASS,
        }
        # Explicit protocol gates.
        g.check("mapback_uses_E11R2_final_mixed_state_without_route_recompute", protocol["mapback_input_contract"]["saturation_state_immutable"])
        g.check("one_common_mapback_operator_for_all_routes", protocol["mapback_input_contract"]["route_label_role"].startswith("detailed provenance subtype"))
        g.check("segment_length_weighted_operator_frozen", protocol["operator_contract"]["deposition_measure"] == "streamline_weight_m3_s * subsegment_length_m")
        g.check("unsupported_cells_nan_no_fill", protocol["operator_contract"]["unsupported_cell_state"] == "NaN" and not protocol["operator_contract"]["unsupported_fill_authorized"])
        g.check("closure_thresholds_1e8", protocol["operator_contract"]["support_closure_relative_max"] == 1e-8 and protocol["operator_contract"]["saturation_measure_closure_relative_max"] == 1e-8)
        g.check("E13_no_full_grid_projection", not protocol["operator_contract"]["global_full_grid_projection_authorized"])
        g.check("E13_no_SG7E_threshold", not protocol["execution_firewall"]["SG7E_thresholding"])
        g.check("E13_requires_independent_post_mapback_audit", "Independent" in protocol["post_E13_required_audit"])

        evidence = {
            "milestone": MILESTONE,
            "status": "PASS",
            "E11R2_frozen": True,
            "E11R2_route_counts": EXPECTED_ROUTE_COUNTS,
            "E11R2_detailed_route_label_counts": EXPECTED_DETAILED_ROUTE_LABEL_COUNTS,
            "blocked_E12_audit_sha256": E12_BLOCKED_AUDIT[1],
            "route_semantics_repair": "blocked E12 counted detailed route_label strings as coarse route classes; R1 uses immutable route_code for class counts",
            "E11R2_zero_unsafe": True,
            "E11R2_pilot_npz_sha256": E11R2["pilot"][1],
            "array_sha256": array_hashes,
            "descriptive_vs_SG7A_truth": audit.get("descriptive_vs_SG7A_truth"),
            "interpretation": "Descriptive SG7A differences remain evidence only; no E12-R1 error threshold is introduced.",
        }
        results = {
            "milestone": MILESTONE,
            "status": "PASS",
            "gates": g.items,
            "mapback_performed": False,
            "training_or_inference_performed": False,
            "E11R2_transport_changed": False,
            "unsupported_cell_policy_executed": False,
            "full_grid_plume_authorized": False,
            "E13_authorized": True,
            "next_milestone": NEXT_PASS,
        }
        summary_out = {
            "milestone": MILESTONE,
            "status": "PASS",
            "evidence_frozen": True,
            "route_counts": EXPECTED_ROUTE_COUNTS,
            "detailed_route_label_counts": EXPECTED_DETAILED_ROUTE_LABEL_COUNTS,
            "route_semantics_reconciled": True,
            "mapback_protocol_frozen": True,
            "mapback_operator": protocol["operator_contract"]["method"],
            "unsupported_cells": "NaN / no fill in E13",
            "mapback_performed": False,
            "E13_authorized": True,
            "full_grid_plume_authorized": False,
            "next_milestone": NEXT_PASS,
        }
        handoff = f"""# PAD-Stream V16E-12-R1 — Route-Semantics Reconciled Pilot Evidence / Map-Back Protocol Freeze PASS\n\nThe blocked V16E-12 route-count interpretation has been repaired without changing E11-R2. V16E-11-R2 remains frozen as the immutable 100-day streamline transport state: 462 Hybrid10 learned accepts, 41 exact-R2 fallbacks, 575 frozen SG7A/full-physics fallbacks, zero Hybrid12 accepts, zero unsafe accepts, and zero unresolved paths.\n\nR1 defines route_code as the canonical coarse execution class and route_label as its detailed provenance subtype. The first V16 conservative map-back must reuse the accepted V15-SG7D1 flow-weighted piecewise-linear segment/cell intersection operator: clip segments to the Cartesian box, split at cell crossings, deposit with streamline_weight * segment_length, linearly interpolate saturation within each segment, and compute supported-cell saturation as numerator/denominator. Unsupported cells remain NaN. Route labels are provenance only and do not select a different grid operator.\n\nNo map-back was executed in E12 or E12-R1. No unsupported-cell fill, full-grid projection, or SG7E thresholding is authorized. E13 is authorized only to execute the frozen supported-cell map-back and must be followed by an independent conservation/support audit.\n\nNEXT: {NEXT_PASS}\n""".encode("utf-8")

        files = {
            "V16E12_R1_SGSim_100Day_Streamline_Pilot_Evidence_Freeze.json": enc(evidence),
            "V16E12_R1_Conservative_MapBack_Protocol.json": enc(protocol),
            "V16E12_R1_Protocol_Freeze_Results.json": enc(results),
            "PAD_Stream_V16E12_R1_Summary.json": enc(summary_out),
            "V16E12_R1_Handoff.md": handoff,
        }
        publish(out, files)

        print("\n" + "="*126)
        print("V16E-12-R1 RESULT: PASS")
        print("="*126)
        print(f"{'E11-R2 streamline evidence frozen':58}: YES")
        print(f"{'Route counts H10 / H12 / R2 / SG7A':58}: 462 / 0 / 41 / 575")
        print(f"{'Route class source / label role':58}: route_code / detailed provenance")
        print(f"{'Map-back operator':58}: V15-SG7D1 segment/cell intersection")
        print(f"{'Deposition measure':58}: streamline weight * segment length")
        print(f"{'Unsupported cells in first map-back':58}: NaN / NO FILL")
        print(f"{'Support / saturation-measure closure max':58}: 1e-8 / 1e-8")
        print(f"{'Map-back executed':58}: NO")
        print(f"{'Full-grid plume authorized':58}: NO")
        print(f"{'Internal test / OOD reopened':58}: NO / NO")
        for name in files:
            print(f"{name} SHA: {sha(out/name)}")
        print("Output:", out)
        print("NEXT:", NEXT_PASS)
        return 0

    except Exception as exc:
        print(f"\n[FAIL] V16E-12-R1 did not close: {exc}")
        try:
            blocked_dir = compute / "provenance/hybrid_dp/V16E12_R1_BLOCKED_ROUTE_SEMANTICS_OR_MAPBACK_PROTOCOL"
            blocked_dir.mkdir(parents=True, exist_ok=True)
            report = {
                "milestone": MILESTONE,
                "status": BLOCKED,
                "exception": repr(exc),
                "gates": g.items,
                "mapback_performed": False,
                "full_grid_plume_authorized": False,
                "next_milestone": NEXT_FAIL,
            }
            p = blocked_dir / "V16E12_R1_Blocked_Audit.json"
            p.write_bytes(enc(report))
            print("Blocked report SHA:", sha(p))
            print("Blocked output:", blocked_dir)
        except Exception:
            pass
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
