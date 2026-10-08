#!/usr/bin/env python3
"""PAD-Stream V16E-16
Controlled Background-Only Unsupported-Cell Completion.

Execution milestone following V16E-15 policy design/audit.

This milestone applies exactly one already-frozen completion rule:

  supported cells   -> preserve V16E-13-R1 saturation_grid_float64 exactly
  unsupported cells -> assign exact frozen constitutive Swc background (=0.2)
  support mask      -> preserve as provenance; filled cells remain unsupported
  numerator/denominator/piece/visit evidence -> preserve unchanged

The completion does NOT create new streamline support and is NOT a new
conservative map-back. No interpolation, nearest-neighbor propagation, route-
specific fill, training, model inference, upstream flow recomputation, or SG7E
thresholding is permitted.

A PASS creates a full-grid candidate only. It does not freeze that candidate and
does not authorize a full-grid plume claim; V16E-17 must independently validate
it first.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import numpy as np

MILESTONE = "V16E-16"
SUCCESS = "V16E16_CONTROLLED_BACKGROUND_ONLY_FULL_GRID_COMPLETION_PASS"
BLOCKED = "V16E16_CONTROLLED_BACKGROUND_ONLY_FULL_GRID_COMPLETION_BLOCKED"
NEXT_PASS = "V16E-17 - Independent Full-Grid Completion Validation"
NEXT_FAIL = "V16E-16-R1 - Repair only the failed completion gate; preserve E13-R1/E14/E15 unchanged"

# -----------------------------------------------------------------------------
# Frozen V16 authority.
# -----------------------------------------------------------------------------
E15_RUNNER = (
    "PAD_Stream_V16E15_SGSim_Unsupported_Cell_Policy_Design_and_Audit.py",
    "a851ec64d85ed019720feffcc4a7f705a100926c8cdf338c934be416f786111c",
)
E15_REL = Path("provenance/hybrid_dp/V16E15_SGSIM_UNSUPPORTED_CELL_POLICY_DESIGN_AUDIT")
E15 = {
    "geometry": ("V16E15_Unsupported_Geometry_Audit.json", "18081e734b6f0bf63c1a5072afdb99a5cf0b9c7149960a4a35602deec3a67db7"),
    "decision": ("V16E15_Policy_Decision.json", "e46c48a13a98fb54b5c07f0cb9d193c85c05aa15177b8a7b8ff87acd9a16eff4"),
    "contract": ("V16E15_Unsupported_Cell_Policy_Contract.json", "5c692ea3b9ba4dee0e43005faeee016c4d442f1d8eb24fa7e21651ddc136f5e0"),
    "audit": ("V16E15_Unsupported_Cell_Policy_Audit.json", "b4c0a414abbb3d0e980ba1c2649d08d4002f2630fbbe2d96b4f922974976f102"),
    "summary": ("PAD_Stream_V16E15_Summary.json", "8df4fcf68d7325ab7db7d9a03bb15478fab609b46dc5a54fafcd201a697b30ba"),
    "handoff": ("V16E15_Handoff.md", "87d6da435e67619c7dba1d822413e8515cccc1037214dfef7e0e7f916105d7d6"),
    "distance": ("V16E15_Unsupported_Distance_to_Support.csv", "1eeb0e04bc0e3c8b02736e6fb55ce290c191af322ae41ce73dbea94ee6f95afc"),
    "neighbors": ("V16E15_Unsupported_Neighbor_Context.csv", "c2ee2c10af7bd9f64506bc935f31cfb25ffb2f83efabf395184a4fd167c45574"),
    "policies": ("V16E15_Candidate_Policy_Audit.csv", "4578e55863a3cc57fc46b2e159e6553f8179ffc43c91424afed75160d5f9d8bd"),
    "layers": ("V16E15_Unsupported_By_Layer.csv", "486169da1474de3963f39da0b79ce30a582ce0500e3031a598ee1ad4ae3918e7"),
    "plume_risk": ("V16E15_Policy_Plume_Risk.csv", "64fb28a9b639acc77d2666693f8913476cc046c0ec3a68778f0b09a1e24770df"),
}
E15_SUCCESS = "V16E15_SGSIM_UNSUPPORTED_CELL_POLICY_DESIGN_AUDIT_PASS"

E13R1_RUNNER = (
    "PAD_Stream_V16E13_R1_Native_Dtype_Identity_Repair_and_Controlled_Conservative_Streamline_to_Grid_MapBack_Execution.py",
    "b8e04c2db9846709c2791afa65d8b10fd9b9e8ada0ac48b0b24cbdf4765e80b6",
)
E13R1_REL = Path("pilots/hybrid_dp/V16E13_R1_SGSIM_100D_CONTROLLED_CONSERVATIVE_MAPBACK")
E13R1 = {
    "numerical": ("V16E13_R1_SGSim_100Day_Conservative_MapBack.npz", "6ef79d6f126a96b7e64a5fb7f9d11164758b9c2726657ff4f7874f0e6acfa79f"),
    "contract": ("V16E13_R1_Conservative_MapBack_Contract.json", "733ced4bb7da6b3c808871f36f73634cd5d3da2290cdde3ca099321fb871a048"),
    "summary": ("PAD_Stream_V16E13_R1_Summary.json", "e6000730fbcb5c97e922033e48f215b00719816f7fb3a7e90474a6631f4d27a5"),
}

E11R2_RUNNER = (
    "PAD_Stream_V16E11_R2_Packed_SG5_Serialization_Repair_and_Controlled_Hybrid_Streamline_Pilot.py",
    "0363a09612c5e80f6bb8124c817ca0d3726b1654283ab169c9b2d4d9861707b7",
)
E11R2_REL = Path("pilots/hybrid_dp/V16E11_R2_SGSIM_100D_CONTROLLED_STREAMLINE_PILOT")
E11R2_PILOT = (
    "V16E11_R2_SGSim_100Day_Streamline_Pilot.npz",
    "710720e933d740787868a9894fa04f90e88429c120d9f86a52b750f4c41db844",
)

# Historical source authority bound by E15.
V15_D4 = (
    "PAD_Stream_V15SG7D4_Controlled_Background_Only_Unsupported_Cell_Completion.py",
    "3e0ce6b780527ae3e0a08ecced4cf7ef92585d6a34d0a16417d2e89064d31ae1",
)
V15_D5 = (
    "PAD_Stream_V15SG7D5_Independent_Full_Grid_Completion_Validation.py",
    "bdf662bda22f7399be66d37eaf2f47a4a58d02af2a87b29a311f4761845fb9a7",
)

OUT_REL = Path("pilots/hybrid_dp/V16E16_SGSIM_100D_CONTROLLED_BACKGROUND_ONLY_FULL_GRID_COMPLETION")
BLOCKED_REL = Path("provenance/hybrid_dp/V16E16_BLOCKED_BACKGROUND_ONLY_FULL_GRID_COMPLETION")

EXPECTED_GRID = (15, 50, 50)
EXPECTED_CELLS = 37500
EXPECTED_SUPPORTED = 20462
EXPECTED_UNSUPPORTED = 17038
EXPECTED_SUPPORT_FRACTION = 0.5456533333333333
EXPECTED_TIME_DAYS = 100.0
EXPECTED_BACKGROUND = 0.2
SELECTED_POLICY = "P4_MASKED_BACKGROUND_PLUS_SUPPORT"
DIAGNOSTIC_THRESHOLD = 0.21  # Historical V15 risk preview only; NOT SG7E.

PROHIBITIONS = [
    "NO CHANGE TO V16E-13-R1, V16E-14, OR V16E-15 ARTIFACTS.",
    "NO MAP-BACK RE-EXECUTION OR NEW CONSERVATIVE PROJECTION.",
    "NO CHANGE TO SUPPORTED-CELL SATURATION VALUES.",
    "NO CHANGE TO SUPPORT MASK / NUMERATOR / DENOMINATOR / PIECE / VISIT EVIDENCE.",
    "NO NEAREST-NEIGHBOR, HARMONIC, OR OTHER INTERPOLATED FILL.",
    "NO ROUTE-SPECIFIC FILL.",
    "NO TRAINING, CHECKPOINT LOAD, OR MODEL INFERENCE.",
    "NO PRESSURE / DARCY / POLLOCK / TOF RECOMPUTATION.",
    "NO SG7E THRESHOLD CHANGE OR FULL-GRID PLUME CLAIM.",
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
    print("PAD-Stream V16E-16 Controlled Background-Only Unsupported-Cell Completion")
    print("=" * 132)
    for line in PROHIBITIONS:
        print(line)

    try:
        # ------------------------------------------------------------------
        # V16E-15 exact policy authority.
        # ------------------------------------------------------------------
        print("\nV16E-15 UNSUPPORTED-CELL POLICY AUTHORITY")
        bind(g, "E15_runner", repo / E15_RUNNER[0], E15_RUNNER[1])
        e15_paths: dict[str, Path] = {}
        for key, (fn, hs) in E15.items():
            p = compute / E15_REL / fn
            bind(g, "E15_" + key, p, hs)
            e15_paths[key] = p

        e15_geometry = read_json(e15_paths["geometry"])
        e15_decision = read_json(e15_paths["decision"])
        e15_contract = read_json(e15_paths["contract"])
        e15_audit = read_json(e15_paths["audit"])
        e15_summary = read_json(e15_paths["summary"])

        g.check("E15_summary_status_PASS", e15_summary.get("status") == "PASS")
        g.check("E15_contract_status_exact", e15_contract.get("status") == E15_SUCCESS)
        g.check("E15_decision_status_PASS", e15_decision.get("status") == "PASS")
        g.check("E15_selected_policy_exact", e15_summary.get("selected_policy") == SELECTED_POLICY and e15_decision.get("selected_policy") == SELECTED_POLICY and e15_contract.get("selected_policy") == SELECTED_POLICY)
        g.check("E15_grid_exact", tuple(e15_summary.get("grid_shape", [])) == EXPECTED_GRID)
        g.check("E15_supported_exact", int(e15_summary.get("supported_cells")) == EXPECTED_SUPPORTED)
        g.check("E15_unsupported_exact", int(e15_summary.get("unsupported_cells")) == EXPECTED_UNSUPPORTED)
        g.check("E15_support_fraction_exact", float(e15_summary.get("support_fraction")) == EXPECTED_SUPPORT_FRACTION)
        g.check("E15_background_exact", float(e15_summary.get("background_saturation")) == EXPECTED_BACKGROUND and float(e15_decision.get("background_saturation_float64")) == EXPECTED_BACKGROUND)
        g.check("E15_background_authority_exact", e15_decision.get("background_authority") == "E11-R2 constitutive_swc")
        g.check("E15_transport_min_representation_matches", e15_decision.get("transport_min_equals_float32_background") is True)
        g.check("E15_background_below_diagnostic", e15_decision.get("background_below_diagnostic_threshold") is True)
        g.check("E15_P4_adds_zero_diagnostic_plume", int(e15_decision.get("P4_added_unsupported_diagnostic_plume_cells")) == 0)
        g.check("E15_no_fill_yet", e15_summary.get("unsupported_cells_filled") is False and e15_summary.get("full_grid_candidate_created") is False)
        g.check("E15_full_grid_plume_not_authorized", e15_summary.get("full_grid_plume_authorized") is False)
        g.check("E15_next_is_E16", str(e15_summary.get("next_milestone", "")).startswith("V16E-16"))
        g.check("E15_geometry_unsupported_components_exact", int(e15_geometry.get("unsupported_component_count")) == 343)
        g.check("E15_geometry_largest_component_exact", int(e15_geometry.get("largest_unsupported_component_cells")) == 16051)
        g.check("E15_geometry_max_distance_exact", int(e15_geometry.get("max_manhattan_distance_to_support")) == 8)

        semantics = e15_contract.get("policy_semantics", {})
        future = e15_contract.get("future_V16E16_execution_gates", {})
        g.check("E15_contract_preserve_supported_semantics", semantics.get("supported_cells") == "preserve V16E-13-R1 saturation_grid_float64 exactly")
        g.check("E15_contract_background_only_semantics", "constitutive Swc background only" in str(semantics.get("unsupported_cells", "")))
        g.check("E15_contract_interpolation_prohibited", semantics.get("interpolation") == "PROHIBITED")
        g.check("E15_contract_nearest_prohibited", semantics.get("nearest_neighbor") == "PROHIBITED")
        g.check("E15_contract_route_specific_fill_prohibited", semantics.get("route_specific_fill") == "PROHIBITED")
        g.check("E15_contract_new_projection_prohibited", semantics.get("new_conservative_projection") == "PROHIBITED")
        required_future = [
            "E13R1_supported_cells_bitwise_unchanged",
            "all_unsupported_equal_background",
            "support_mask_hash_unchanged",
            "support_numerator_hash_unchanged",
            "support_denominator_hash_unchanged",
            "full_grid_all_finite",
            "no_interpolation",
            "no_nearest_neighbor",
            "independent_V16E17_validation_required_before_freeze",
        ]
        g.check("E15_future_E16_gates_all_authorized", all(future.get(k) is True for k in required_future), str({k: future.get(k) for k in required_future}))
        g.check("E15_future_E16_zero_unsupported_diagnostic_plume", int(future.get("unsupported_diagnostic_plume_cells")) == 0)
        firewall = e15_audit.get("firewall", {})
        g.check("E15_firewall_no_grid_change", firewall.get("grid_values_modified") is False and firewall.get("unsupported_cells_filled") is False)

        # ------------------------------------------------------------------
        # Historical V15 completion / independent-validation authority.
        # ------------------------------------------------------------------
        print("\nVERSION-15 BACKGROUND-COMPLETION SOURCE AUTHORITY")
        d4_path = repo / V15_D4[0]
        d5_path = repo / V15_D5[0]
        bind(g, "V15SG7D4_source", d4_path, V15_D4[1])
        bind(g, "V15SG7D5_source", d5_path, V15_D5[1])
        g.check("V15SG7D4_exact_P4_semantics_present", source_contains(d4_path, [
            "P4_MASKED_BACKGROUND_PLUS_SUPPORT",
            "supported cells   -> preserve SG7D1 exactly",
            "unsupported cells -> assign frozen transport background saturation only",
            "NO INTERPOLATION",
            "NO NEAREST-NEIGHBOR FILL",
            "supported_cells_exactly_preserved",
            "unsupported_cells_equal_background",
            "support_mask_preserved",
            "conservative_numerator_preserved",
            "conservative_denominator_preserved",
        ]))
        g.check("V15SG7D5_independent_validation_required_semantics_present", source_contains(d5_path, [
            "full_grid_float32_reconstruction_exact",
            "supported_cells_preserved",
            "unsupported_cells_equal_frozen_background",
            "conservative_denominator_preserved",
            "conservative_numerator_preserved",
            "no_interpolation_used",
            "no_nearest_neighbor_used",
        ]))

        # ------------------------------------------------------------------
        # E13-R1 supported conservative map-back authority.
        # ------------------------------------------------------------------
        print("\nV16E-13-R1 SUPPORTED-CELL NUMERICAL AUTHORITY")
        bind(g, "E13R1_runner", repo / E13R1_RUNNER[0], E13R1_RUNNER[1])
        e13_paths: dict[str, Path] = {}
        for key, (fn, hs) in E13R1.items():
            p = compute / E13R1_REL / fn
            bind(g, "E13R1_" + key, p, hs)
            e13_paths[key] = p

        e13_contract = read_json(e13_paths["contract"])
        e13_summary = read_json(e13_paths["summary"])
        g.check("E13R1_status_PASS", e13_summary.get("status") == "PASS")
        g.check("E13R1_supported_exact", int(e13_summary.get("supported_cells")) == EXPECTED_SUPPORTED)
        g.check("E13R1_unsupported_exact", int(e13_summary.get("unsupported_cells")) == EXPECTED_UNSUPPORTED)
        g.check("E13R1_unsupported_not_filled", e13_summary.get("unsupported_cells_filled") is False)
        g.check("E13R1_full_grid_not_authorized", e13_summary.get("full_grid_plume_authorized") is False)

        with np.load(e13_paths["numerical"], allow_pickle=False) as db:
            required = [
                "saturation_grid_float64", "support_denominator", "support_numerator",
                "supported_mask", "segment_piece_count", "streamline_visit_count",
                "physical_time_days", "grid_shape",
            ]
            g.check("E13R1_required_arrays_present", all(k in db.files for k in required), str(db.files))
            s_supported = np.array(db["saturation_grid_float64"], dtype=np.float64, copy=True)
            den = np.array(db["support_denominator"], dtype=np.float64, copy=True)
            num = np.array(db["support_numerator"], dtype=np.float64, copy=True)
            support_stored = np.array(db["supported_mask"], copy=True).astype(bool)
            pieces = np.array(db["segment_piece_count"], dtype=np.int64, copy=True)
            visits = np.array(db["streamline_visit_count"], dtype=np.int64, copy=True)
            grid_shape = tuple(int(x) for x in np.asarray(db["grid_shape"]).tolist())
            time_days = float(np.asarray(db["physical_time_days"]))

        g.check("E13R1_grid_shape_exact", grid_shape == EXPECTED_GRID)
        g.check("E13R1_time_100d", time_days == EXPECTED_TIME_DAYS)
        g.check("E13R1_arrays_shape_exact", all(a.shape == EXPECTED_GRID for a in [s_supported, den, num, support_stored, pieces, visits]))
        support = den > 0.0
        unsupported = ~support
        g.check("support_mask_reproduced", np.array_equal(support, support_stored))
        g.check("supported_count_exact", int(np.sum(support)) == EXPECTED_SUPPORTED)
        g.check("unsupported_count_exact", int(np.sum(unsupported)) == EXPECTED_UNSUPPORTED)
        g.check("supported_finite", np.all(np.isfinite(s_supported[support])))
        g.check("unsupported_explicit_nan_before_completion", np.all(np.isnan(s_supported[unsupported])))
        g.check("piece_visit_support_consistency", np.all(pieces[support] > 0) and np.all(visits[support] > 0) and np.all(pieces[unsupported] == 0) and np.all(visits[unsupported] == 0))

        recorded_arrays = e13_contract.get("array_sha256", {})
        support_u8 = support.astype(np.uint8)
        g.check("E13R1_saturation_array_SHA_exact", arr_sha(s_supported) == recorded_arrays.get("saturation_grid_float64"))
        g.check("E13R1_denominator_array_SHA_exact", arr_sha(den) == recorded_arrays.get("support_denominator"))
        g.check("E13R1_numerator_array_SHA_exact", arr_sha(num) == recorded_arrays.get("support_numerator"))
        g.check("E13R1_support_array_SHA_exact", arr_sha(support_u8) == recorded_arrays.get("supported_mask"))

        # ------------------------------------------------------------------
        # Direct E11-R2 background authority.
        # ------------------------------------------------------------------
        print("\nV16E-11-R2 FROZEN BACKGROUND AUTHORITY")
        bind(g, "E11R2_runner", repo / E11R2_RUNNER[0], E11R2_RUNNER[1])
        pilot_path = compute / E11R2_REL / E11R2_PILOT[0]
        bind(g, "E11R2_pilot", pilot_path, E11R2_PILOT[1])
        with np.load(pilot_path, allow_pickle=False) as db:
            g.check("E11R2_background_keys_present", "saturation_100d" in db.files and "constitutive_swc" in db.files)
            sat_native = np.array(db["saturation_100d"], copy=True)
            swc = float(np.asarray(db["constitutive_swc"]))
        g.check("E11R2_swc_exact_0p2", swc == EXPECTED_BACKGROUND, f"{swc:.17g}")
        g.check("E11R2_saturation_native_float32", sat_native.dtype == np.float32, str(sat_native.dtype))
        g.check("E11R2_transport_min_matches_float32_Swc", float(np.min(sat_native)) == float(np.float32(swc)))
        g.check("background_matches_E15_exact", swc == float(e15_decision.get("background_saturation_float64")))
        background = np.float64(swc)

        # ------------------------------------------------------------------
        # Controlled P4 completion -- the ONLY grid modification in E16.
        # ------------------------------------------------------------------
        print("\nCONTROLLED P4 BACKGROUND-ONLY FULL-GRID COMPLETION")
        before_hashes = {
            "supported_state": arr_sha(s_supported),
            "support_mask": arr_sha(support_u8),
            "support_denominator": arr_sha(den),
            "support_numerator": arr_sha(num),
            "segment_piece_count": arr_sha(pieces),
            "streamline_visit_count": arr_sha(visits),
        }

        full_grid = np.array(s_supported, dtype=np.float64, copy=True)
        full_grid[unsupported] = background

        # Deterministic replay of the same frozen algebra.
        full_grid_repeat = np.array(s_supported, dtype=np.float64, copy=True)
        full_grid_repeat[unsupported] = background

        g.check("deterministic_repeat_exact", np.array_equal(full_grid, full_grid_repeat) and arr_sha(full_grid) == arr_sha(full_grid_repeat))
        g.check("supported_cells_bitwise_unchanged", np.array_equal(full_grid[support], s_supported[support]))
        g.check("unsupported_cells_equal_exact_background", np.all(full_grid[unsupported] == background))
        g.check("full_grid_all_finite", np.all(np.isfinite(full_grid)))
        g.check("full_grid_shape_exact", full_grid.shape == EXPECTED_GRID)
        g.check("full_grid_cell_count_exact", full_grid.size == EXPECTED_CELLS)
        g.check("support_mask_unchanged", arr_sha(support_u8) == before_hashes["support_mask"])
        g.check("support_denominator_unchanged", arr_sha(den) == before_hashes["support_denominator"])
        g.check("support_numerator_unchanged", arr_sha(num) == before_hashes["support_numerator"])
        g.check("segment_piece_count_unchanged", arr_sha(pieces) == before_hashes["segment_piece_count"])
        g.check("streamline_visit_count_unchanged", arr_sha(visits) == before_hashes["streamline_visit_count"])
        g.check("background_filled_cells_remain_unsupported", np.all(~support[unsupported]) and int(np.sum(support)) == EXPECTED_SUPPORTED)

        supported_min = float(np.min(s_supported[support]))
        supported_max = float(np.max(s_supported[support]))
        full_min = float(np.min(full_grid))
        full_max = float(np.max(full_grid))
        g.check("full_grid_lower_bound_exact_background", full_min == float(background), f"{full_min:.17g}")
        g.check("full_grid_upper_bound_preserves_supported_max", full_max == supported_max, f"{full_max:.17g}")
        g.check("full_grid_physical_bounds", full_min >= EXPECTED_BACKGROUND and full_max <= 1.0)

        # Historical 0.21 threshold is diagnostic only; no SG7E decision is made.
        supported_plume_before = support & np.isfinite(s_supported) & (s_supported >= DIAGNOSTIC_THRESHOLD)
        supported_plume_after = support & (full_grid >= DIAGNOSTIC_THRESHOLD)
        unsupported_diagnostic_plume = unsupported & (full_grid >= DIAGNOSTIC_THRESHOLD)
        full_diagnostic_plume = full_grid >= DIAGNOSTIC_THRESHOLD
        supported_plume_cells = int(np.sum(supported_plume_before))
        unsupported_plume_cells = int(np.sum(unsupported_diagnostic_plume))
        g.check("supported_diagnostic_membership_exact", np.array_equal(supported_plume_before, supported_plume_after))
        g.check("supported_diagnostic_plume_count_matches_E15", supported_plume_cells == int(e15_decision.get("supported_diagnostic_plume_cells")))
        g.check("unsupported_background_adds_zero_diagnostic_plume", unsupported_plume_cells == 0)
        g.check("full_diagnostic_plume_equals_supported_reference", np.array_equal(full_diagnostic_plume, supported_plume_before))
        before_components = connected_components_3d(supported_plume_before)
        after_components = connected_components_3d(full_diagnostic_plume)
        g.check("diagnostic_plume_topology_preserved", before_components == after_components)

        after_hashes = {
            "supported_state": arr_sha(s_supported),
            "full_grid": arr_sha(full_grid),
            "support_mask": arr_sha(support_u8),
            "support_denominator": arr_sha(den),
            "support_numerator": arr_sha(num),
            "segment_piece_count": arr_sha(pieces),
            "streamline_visit_count": arr_sha(visits),
        }
        g.check("all_conservative_evidence_hashes_preserved", all(after_hashes[k] == before_hashes[k] for k in ["support_mask", "support_denominator", "support_numerator", "segment_piece_count", "streamline_visit_count"]))
        g.check("only_unsupported_state_values_completed", True)
        g.check("no_interpolation_used", True)
        g.check("no_nearest_neighbor_used", True)
        g.check("no_route_specific_fill_used", True)
        g.check("no_new_conservative_projection", True)
        g.check("full_grid_candidate_not_frozen_in_E16", True)
        g.check("independent_E17_required", True)

        # ------------------------------------------------------------------
        # Persist candidate + immutable provenance evidence.
        # ------------------------------------------------------------------
        out.mkdir(parents=True, exist_ok=True)
        numerical = out / "V16E16_SGSim_100Day_Background_Completed_Full_Grid.npz"
        np.savez_compressed(
            numerical,
            saturation_grid_full_float64=full_grid.astype(np.float64, copy=False),
            saturation_grid_supported_only_float64=s_supported.astype(np.float64, copy=False),
            supported_mask=support_u8,
            support_denominator=den.astype(np.float64, copy=False),
            support_numerator=num.astype(np.float64, copy=False),
            segment_piece_count=pieces.astype(np.int64, copy=False),
            streamline_visit_count=visits.astype(np.int64, copy=False),
            background_saturation=np.asarray(background, dtype=np.float64),
            diagnostic_threshold=np.asarray(DIAGNOSTIC_THRESHOLD, dtype=np.float64),
            physical_time_days=np.asarray(EXPECTED_TIME_DAYS, dtype=np.float64),
            grid_shape=np.asarray(EXPECTED_GRID, dtype=np.int64),
            source_E13R1_numerical_sha256=np.asarray(E13R1["numerical"][1]),
            source_E15_contract_sha256=np.asarray(E15["contract"][1]),
        )

        completion_audit = {
            "milestone": MILESTONE,
            "status": "PASS",
            "selected_policy": SELECTED_POLICY,
            "physical_time_days": EXPECTED_TIME_DAYS,
            "grid_shape": list(EXPECTED_GRID),
            "supported_cells": EXPECTED_SUPPORTED,
            "unsupported_cells_completed": EXPECTED_UNSUPPORTED,
            "support_fraction": EXPECTED_SUPPORT_FRACTION,
            "background_saturation": float(background),
            "supported_state_Linf_change": float(np.max(np.abs(full_grid[support] - s_supported[support]))),
            "unsupported_background_Linf_error": float(np.max(np.abs(full_grid[unsupported] - background))),
            "full_grid_min": full_min,
            "full_grid_max": full_max,
            "full_grid_all_finite": bool(np.all(np.isfinite(full_grid))),
            "deterministic_repeat_exact": True,
            "supported_diagnostic_plume_cells_before": supported_plume_cells,
            "supported_diagnostic_plume_cells_after": int(np.sum(supported_plume_after)),
            "unsupported_diagnostic_plume_cells_after": unsupported_plume_cells,
            "diagnostic_plume_component_sizes_before": before_components,
            "diagnostic_plume_component_sizes_after": after_components,
            "diagnostic_threshold": DIAGNOSTIC_THRESHOLD,
            "diagnostic_threshold_semantics": "HISTORICAL_V15_COMPLETION_PRESERVATION_CHECK_ONLY_NOT_SG7E",
            "array_sha256_before": before_hashes,
            "array_sha256_after": after_hashes,
            "support_semantics": "background-completed cells remain unsupported; support mask is unchanged",
            "full_grid_candidate_created": True,
            "candidate_frozen": False,
            "full_grid_plume_authorized": False,
            "next_milestone": NEXT_PASS,
        }
        contract = {
            "milestone": MILESTONE,
            "status": SUCCESS,
            "selected_policy": SELECTED_POLICY,
            "completion_equation": "S_full[c] = S_E13R1[c] if supported[c], else constitutive Swc",
            "background_authority": "E11-R2 constitutive_swc",
            "background_saturation": float(background),
            "preservation_contract": {
                "supported_cells": "bitwise/numerically exact V16E-13-R1 float64 values",
                "support_mask": "exactly unchanged and retained as support provenance",
                "support_denominator": "exactly unchanged; conservative evidence for supported cells only",
                "support_numerator": "exactly unchanged; conservative evidence for supported cells only",
                "segment_piece_count": "exactly unchanged",
                "streamline_visit_count": "exactly unchanged",
                "unsupported_cells": "exact frozen constitutive Swc background",
                "interpolation": "PROHIBITED",
                "nearest_neighbor": "PROHIBITED",
                "route_specific_fill": "PROHIBITED",
                "new_conservative_projection": "PROHIBITED",
            },
            "array_sha256": after_hashes,
            "source_authority": {
                "E15_runner_sha256": E15_RUNNER[1],
                "E15_artifacts": {k: {"file": v[0], "sha256": v[1]} for k, v in E15.items()},
                "E13R1_runner_sha256": E13R1_RUNNER[1],
                "E13R1_artifacts": {k: {"file": v[0], "sha256": v[1]} for k, v in E13R1.items()},
                "E11R2_runner_sha256": E11R2_RUNNER[1],
                "E11R2_pilot_sha256": E11R2_PILOT[1],
                "V15SG7D4_source_sha256": V15_D4[1],
                "V15SG7D5_source_sha256": V15_D5[1],
            },
            "independent_validation_required": True,
            "candidate_frozen": False,
            "full_grid_plume_authorized": False,
            "next_milestone": NEXT_PASS,
        }
        manifest = {
            "milestone": MILESTONE,
            "status": SUCCESS,
            "candidate": "V16E16_background_completed_full_grid_float64",
            "numerical_file": numerical.name,
            "numerical_file_sha256": "PENDING_UNTIL_SERIALIZED",
            "candidate_array_sha256": after_hashes["full_grid"],
            "supported_source_array_sha256": before_hashes["supported_state"],
            "support_mask_array_sha256": after_hashes["support_mask"],
            "support_denominator_array_sha256": after_hashes["support_denominator"],
            "support_numerator_array_sha256": after_hashes["support_numerator"],
            "background_saturation": float(background),
            "supported_cells": EXPECTED_SUPPORTED,
            "background_completed_cells": EXPECTED_UNSUPPORTED,
            "candidate_frozen": False,
            "independent_validation_required": True,
            "full_grid_plume_authorized": False,
            "next_milestone": NEXT_PASS,
        }
        summary = {
            "milestone": MILESTONE,
            "status": "PASS",
            "physical_time_days": EXPECTED_TIME_DAYS,
            "grid_shape": list(EXPECTED_GRID),
            "supported_cells_preserved": EXPECTED_SUPPORTED,
            "unsupported_cells_completed": EXPECTED_UNSUPPORTED,
            "full_grid_cells": EXPECTED_CELLS,
            "background_saturation": float(background),
            "full_grid_min": full_min,
            "full_grid_max": full_max,
            "supported_state_Linf_change": completion_audit["supported_state_Linf_change"],
            "unsupported_background_Linf_error": completion_audit["unsupported_background_Linf_error"],
            "deterministic_repeat_exact": True,
            "unsupported_diagnostic_plume_cells": unsupported_plume_cells,
            "support_mask_preserved": True,
            "conservative_evidence_preserved": True,
            "full_grid_candidate_created": True,
            "candidate_frozen": False,
            "full_grid_plume_authorized": False,
            "independent_validation_required": True,
            "next_milestone": NEXT_PASS,
        }

        # Numerical-file SHA can be inserted in all metadata only after NPZ exists.
        numerical_sha = sha(numerical)
        manifest["numerical_file_sha256"] = numerical_sha
        contract["numerical_file_sha256"] = numerical_sha
        completion_audit["numerical_file_sha256"] = numerical_sha
        summary["numerical_file_sha256"] = numerical_sha

        handoff = f"""# PAD-Stream V16E-16 - Controlled Background-Only Unsupported-Cell Completion PASS

The V16E-15 P4 policy was executed exactly once on the accepted V16E-13-R1 supported-cell candidate.

- Supported cells preserved exactly: {EXPECTED_SUPPORTED}
- Unsupported cells completed with constitutive Swc={float(background):.17g}: {EXPECTED_UNSUPPORTED}
- Full grid cells: {EXPECTED_CELLS}
- Supported-state Linf change: {completion_audit['supported_state_Linf_change']:.17g}
- Unsupported-background Linf error: {completion_audit['unsupported_background_Linf_error']:.17g}
- Support mask / numerator / denominator / piece / visit evidence: unchanged
- Interpolation / nearest-neighbor / route-specific fill: not used
- Background-completed cells remain unsupported in provenance
- Candidate created: YES
- Candidate frozen: NO
- Full-grid plume authorized: NO
- Independent V16E-17 validation required before freeze: YES

NEXT: {NEXT_PASS}
""".encode("utf-8")

        files = {
            "V16E16_Background_Completion_Audit.json": enc(completion_audit),
            "V16E16_Background_Completion_Contract.json": enc(contract),
            "V16E16_Full_Grid_Candidate_Manifest.json": enc(manifest),
            "PAD_Stream_V16E16_Summary.json": enc(summary),
            "V16E16_Handoff.md": handoff,
        }
        for name, data in files.items():
            atomic_write(out / name, data)

        print("\n" + "=" * 132)
        print("V16E-16 RESULT: PASS")
        print("=" * 132)
        print(f"{'SGSim grid':66}: 15 x 50 x 50")
        print(f"{'Supported cells preserved exactly':66}: {EXPECTED_SUPPORTED}")
        print(f"{'Unsupported cells completed with background':66}: {EXPECTED_UNSUPPORTED}")
        print(f"{'Frozen background saturation Swc':66}: {float(background):.17g}")
        print(f"{'Supported-state Linf change':66}: {completion_audit['supported_state_Linf_change']:.17g}")
        print(f"{'Unsupported-background Linf error':66}: {completion_audit['unsupported_background_Linf_error']:.17g}")
        print(f"{'Full-grid min / max':66}: {full_min:.17g} / {full_max:.17g}")
        print(f"{'Unsupported diagnostic plume cells':66}: {unsupported_plume_cells}")
        print(f"{'Deterministic repeat exact':66}: YES")
        print(f"{'Support/conservative evidence preserved':66}: YES")
        print(f"{'Full-grid candidate created':66}: YES")
        print(f"{'Candidate frozen':66}: NO")
        print(f"{'Full-grid plume authorized':66}: NO")
        print(f"{'Independent V16E-17 validation required':66}: YES")
        print(f"{numerical.name} SHA: {numerical_sha}")
        for name in files:
            print(f"{name} SHA: {sha(out / name)}")
        print("Output:", out)
        print("NEXT:", NEXT_PASS)
        return 0

    except Exception as exc:
        print(f"\n[FAIL] V16E-16 did not close: {exc}", flush=True)
        try:
            bdir = compute / BLOCKED_REL
            bdir.mkdir(parents=True, exist_ok=True)
            report = {
                "milestone": MILESTONE,
                "status": BLOCKED,
                "exception": repr(exc),
                "gates": g.items,
                "E13R1_modified": False,
                "E14_modified": False,
                "E15_modified": False,
                "mapback_reexecuted": False,
                "interpolation_used": False,
                "nearest_neighbor_used": False,
                "full_grid_candidate_accepted": False,
                "candidate_frozen": False,
                "full_grid_plume_authorized": False,
                "next_milestone": NEXT_FAIL,
            }
            p = bdir / "V16E16_Blocked_Background_Only_Completion_Audit.json"
            atomic_write(p, enc(report))
            print("Blocked report SHA:", sha(p))
            print("Blocked output:", bdir)
        except Exception:
            pass
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
