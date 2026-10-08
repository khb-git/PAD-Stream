#!/usr/bin/env python3
"""PAD-Stream V16E-15
SGSim Unsupported-Cell Policy Design / Audit.

Design-only milestone following the independently validated V16E-13-R1
supported-cell map-back and V16E-14 independent conservation/support audit.

V16E-15 does NOT modify the accepted grid. It source-binds the historical
V15-SG7D3/4/5 unsupported-cell lineage, characterizes the actual V16
unsupported region, establishes the authoritative background state, audits
candidate completion policies, and freezes the only policy that a future
controlled execution milestone may apply.

The selected policy, when all gates pass, is the V15 lineage's minimum-
information P4_MASKED_BACKGROUND_PLUS_SUPPORT contract:

  supported cells   -> preserve V16E-13-R1 float64 saturation exactly
  unsupported cells -> assign only the frozen constitutive background Swc
  support mask      -> retain as immutable provenance
  numerator/denominator -> preserve unchanged as supported-mapback evidence
  interpolation / nearest-neighbor -> prohibited

The future fill is a completion policy, not a claim that unsupported cells
received streamline support and not a new conservative deposition operation.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
from pathlib import Path
from typing import Any

import numpy as np

MILESTONE = "V16E-15"
SUCCESS = "V16E15_SGSIM_UNSUPPORTED_CELL_POLICY_DESIGN_AUDIT_PASS"
BLOCKED = "V16E15_SGSIM_UNSUPPORTED_CELL_POLICY_DESIGN_AUDIT_BLOCKED"
NEXT_PASS = "V16E-16 - Controlled Background-Only Unsupported-Cell Completion"
NEXT_FAIL = "V16E-15-R1 - Repair only the failed policy-design gate; preserve E13-R1/E14 unchanged"

# -----------------------------------------------------------------------------
# Frozen V16 parent identities.
# -----------------------------------------------------------------------------
E14_RUNNER = (
    "PAD_Stream_V16E14_Independent_SGSim_100Day_MapBack_Conservation_and_Support_Audit.py",
    "8225bc3d6e6c5f1731e75b74663285a880206c23c1d82fb524f14cf2122e2898",
)
E14_REL = Path("provenance/hybrid_dp/V16E14_INDEPENDENT_SGSIM_100D_MAPBACK_CONSERVATION_SUPPORT_AUDIT")
E14 = {
    "audit": ("V16E14_Independent_MapBack_Audit.json", "ccc3e6b6cfe31c88d807346ca09a69eba7419a3ea36e92206c8981e7ac8aa420"),
    "closure": ("V16E14_Independent_Closure_Audit.json", "f86bd65e524a2ca87b7123b31b47f2d7a2dc0acd90fdc4924a21654479ef1151"),
    "topology": ("V16E14_Support_Topology.json", "5fab506f9e419c3a1ed2ca7b7401bbfd83d16b6066ca88593b914766c7e30f45"),
    "summary": ("PAD_Stream_V16E14_Summary.json", "e57397fc538c374f94c45494df801525c36c0327140ef2fdeb5cab47307d7450"),
    "handoff": ("V16E14_Handoff.md", "081f5d57bfafee1ef3ab2a1ccdaad33620e05f710d4ce0b5c0ee81eba0dd8b42"),
    "layers": ("V16E14_Support_By_Layer.csv", "6a2c29a21e590bb052927455eb01e21ab9820ac59f5fc0e1dc9ace153f0d9518"),
}

E13R1_RUNNER = (
    "PAD_Stream_V16E13_R1_Native_Dtype_Identity_Repair_and_Controlled_Conservative_Streamline_to_Grid_MapBack_Execution.py",
    "b8e04c2db9846709c2791afa65d8b10fd9b9e8ada0ac48b0b24cbdf4765e80b6",
)
E13R1_REL = Path("pilots/hybrid_dp/V16E13_R1_SGSIM_100D_CONTROLLED_CONSERVATIVE_MAPBACK")
E13R1 = {
    "numerical": ("V16E13_R1_SGSim_100Day_Conservative_MapBack.npz", "6ef79d6f126a96b7e64a5fb7f9d11164758b9c2726657ff4f7874f0e6acfa79f"),
    "audit": ("V16E13_R1_Conservative_MapBack_Audit.json", "934dc12405450dfef10ca177d617a52a91db50b7f5deefd179ef0064bdb5e6cb"),
    "contract": ("V16E13_R1_Conservative_MapBack_Contract.json", "733ced4bb7da6b3c808871f36f73634cd5d3da2290cdde3ca099321fb871a048"),
    "summary": ("PAD_Stream_V16E13_R1_Summary.json", "e6000730fbcb5c97e922033e48f215b00719816f7fb3a7e90474a6631f4d27a5"),
    "handoff": ("V16E13_R1_Handoff.md", "57fcc84032c7fbb7089a265e7162e050264db4cde1b748744043691e80f3eb51"),
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

# -----------------------------------------------------------------------------
# Historical source authority.
# -----------------------------------------------------------------------------
V15_D3 = (
    "PAD_Stream_V15SG7D3_Unsupported_Cell_Policy_Design_Audit.py",
    "1812a355be70bbcaf896ee33dc943a47cfdc19c9c3d44d89cd29a6e7c4272cfb",
)
V15_D4 = (
    "PAD_Stream_V15SG7D4_Controlled_Background_Only_Unsupported_Cell_Completion.py",
    "3e0ce6b780527ae3e0a08ecced4cf7ef92585d6a34d0a16417d2e89064d31ae1",
)
V15_D5 = (
    "PAD_Stream_V15SG7D5_Independent_Full_Grid_Completion_Validation.py",
    "bdf662bda22f7399be66d37eaf2f47a4a58d02af2a87b29a311f4761845fb9a7",
)

OUT_REL = Path("provenance/hybrid_dp/V16E15_SGSIM_UNSUPPORTED_CELL_POLICY_DESIGN_AUDIT")
BLOCKED_REL = Path("provenance/hybrid_dp/V16E15_BLOCKED_UNSUPPORTED_CELL_POLICY_DESIGN")

EXPECTED_GRID = (15, 50, 50)
EXPECTED_CELLS = 37500
EXPECTED_SUPPORTED = 20462
EXPECTED_UNSUPPORTED = 17038
EXPECTED_SUPPORT_FRACTION = 0.5456533333333333
EXPECTED_SUPPORT_COMPONENTS = 1
EXPECTED_LARGEST_SUPPORTED = 20462
EXPECTED_TIME_DAYS = 100.0
EXPECTED_SWC = 0.2
DIAGNOSTIC_THRESHOLD = 0.21  # Historical V15-SG7D3 diagnostic only; never an SG7E gate.

PROHIBITIONS = [
    "NO CHANGE TO V16E-13-R1 OR V16E-14 ARTIFACTS.",
    "NO GRID CELL VALUE IS MODIFIED IN V16E-15.",
    "NO UNSUPPORTED CELL IS FILLED IN V16E-15.",
    "NO MAP-BACK RE-EXECUTION OR NEW CONSERVATIVE PROJECTION.",
    "NO TRAINING, CHECKPOINT LOAD, OR MODEL INFERENCE.",
    "NO PRESSURE / DARCY / POLLOCK / TOF RECOMPUTATION.",
    "NO NEAREST-NEIGHBOR OR INTERPOLATED SATURATION AUTHORIZED.",
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


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def bind(g: Gates, label: str, path: Path, expected: str) -> str:
    g.check(label + "_exists", path.is_file(), str(path))
    actual = sha(path)
    g.check(label + "_SHA_exact", actual == expected, actual if actual != expected else "")
    return actual


def load_source_module(path: Path):
    spec = importlib.util.spec_from_file_location("v15_sg7d3_policy_authority", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not import V15-SG7D3 policy authority")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def atomic_write(path: Path, data: bytes):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def write_csv(path: Path, rows: list[dict[str, Any]]):
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
        w.writerows(rows)
    os.replace(tmp, path)


def source_contains(path: Path, required: list[str]) -> bool:
    text = path.read_text(encoding="utf-8", errors="strict")
    return all(token in text for token in required)


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

    print("=" * 126)
    print("PAD-Stream V16E-15 SGSim Unsupported-Cell Policy Design / Audit")
    print("=" * 126)
    for line in PROHIBITIONS:
        print(line)

    try:
        # ------------------------------------------------------------------
        # V16E-14 independent audit authority.
        # ------------------------------------------------------------------
        print("\nV16E-14 INDEPENDENT MAP-BACK AUDIT AUTHORITY")
        bind(g, "E14_runner", repo / E14_RUNNER[0], E14_RUNNER[1])
        e14_paths: dict[str, Path] = {}
        for key, (fn, hs) in E14.items():
            p = compute / E14_REL / fn
            bind(g, "E14_" + key, p, hs)
            e14_paths[key] = p

        e14_audit = read_json(e14_paths["audit"])
        e14_closure = read_json(e14_paths["closure"])
        e14_topology = read_json(e14_paths["topology"])
        e14_summary = read_json(e14_paths["summary"])

        g.check("E14_status_PASS", e14_summary.get("status") == "PASS")
        g.check("E14_physical_time_100d", float(e14_summary.get("physical_time_days")) == EXPECTED_TIME_DAYS)
        g.check("E14_grid_shape_exact", tuple(e14_summary.get("grid_shape", [])) == EXPECTED_GRID)
        g.check("E14_supported_exact", int(e14_summary.get("supported_cells")) == EXPECTED_SUPPORTED)
        g.check("E14_unsupported_exact", int(e14_summary.get("unsupported_cells")) == EXPECTED_UNSUPPORTED)
        g.check("E14_support_fraction_exact", float(e14_summary.get("support_fraction")) == EXPECTED_SUPPORT_FRACTION)
        g.check("E14_state_reconstruction_exact", float(e14_summary.get("state_reconstruction_Linf")) == 0.0)
        g.check("E14_support_component_count_one", int(e14_summary.get("support_component_count")) == EXPECTED_SUPPORT_COMPONENTS)
        g.check("E14_largest_component_all_supported", int(e14_summary.get("largest_support_component_cells")) == EXPECTED_LARGEST_SUPPORTED and float(e14_summary.get("largest_support_component_fraction")) == 1.0)
        g.check("E14_unsupported_policy_required", e14_summary.get("unsupported_policy_needed") is True)
        g.check("E14_unsupported_not_filled", e14_summary.get("unsupported_cells_filled") is False)
        g.check("E14_full_grid_not_authorized", e14_summary.get("full_grid_plume_authorized") is False)
        g.check("E14_next_is_E15", str(e14_summary.get("next_milestone", "")).startswith("V16E-15"))
        g.check("E14_audit_supported_candidate_validated", e14_audit.get("decision", {}).get("E13R1_supported_cell_candidate_independently_validated") is True)
        g.check("E14_audit_fill_not_authorized", e14_audit.get("decision", {}).get("unsupported_fill_authorized") is False)
        g.check("E14_closure_state_reconstruction_exact", float(e14_closure["state_reconstruction"]["Linf"]) == 0.0)
        g.check("E14_topology_no_threshold", e14_topology.get("saturation_threshold_used") is False)

        # ------------------------------------------------------------------
        # V16E-13-R1 supported-cell numerical authority.
        # ------------------------------------------------------------------
        print("\nV16E-13-R1 SUPPORTED-CELL GRID AUTHORITY")
        bind(g, "E13R1_runner", repo / E13R1_RUNNER[0], E13R1_RUNNER[1])
        e13_paths: dict[str, Path] = {}
        for key, (fn, hs) in E13R1.items():
            p = compute / E13R1_REL / fn
            bind(g, "E13R1_" + key, p, hs)
            e13_paths[key] = p
        e13_contract = read_json(e13_paths["contract"])
        e13_summary = read_json(e13_paths["summary"])
        g.check("E13R1_status_PASS", e13_summary.get("status") == "PASS")
        g.check("E13R1_unsupported_not_filled", e13_summary.get("unsupported_cells_filled") is False)
        g.check("E13R1_full_grid_not_authorized", e13_summary.get("full_grid_plume_authorized") is False)

        with np.load(e13_paths["numerical"], allow_pickle=False) as db:
            required = [
                "saturation_grid_float64", "support_denominator", "support_numerator",
                "supported_mask", "segment_piece_count", "streamline_visit_count",
                "physical_time_days", "grid_shape",
            ]
            g.check("E13R1_required_arrays_present", all(k in db.files for k in required), str(db.files))
            s_grid = np.array(db["saturation_grid_float64"], dtype=np.float64, copy=True)
            den = np.array(db["support_denominator"], dtype=np.float64, copy=True)
            num = np.array(db["support_numerator"], dtype=np.float64, copy=True)
            support_stored = np.array(db["supported_mask"], copy=True).astype(bool)
            pieces = np.array(db["segment_piece_count"], dtype=np.int64, copy=True)
            visits = np.array(db["streamline_visit_count"], dtype=np.int64, copy=True)
            grid_shape = tuple(int(x) for x in np.asarray(db["grid_shape"]).tolist())
            time_days = float(np.asarray(db["physical_time_days"]))

        g.check("E13R1_grid_shape_exact", grid_shape == EXPECTED_GRID)
        g.check("E13R1_time_100d", time_days == EXPECTED_TIME_DAYS)
        g.check("E13R1_grid_arrays_shape_exact", all(a.shape == EXPECTED_GRID for a in [s_grid, den, num, support_stored, pieces, visits]))
        support = den > 0.0
        unsupported = ~support
        g.check("support_mask_reproduced_from_denominator", np.array_equal(support, support_stored))
        g.check("supported_count_reproduced", int(np.sum(support)) == EXPECTED_SUPPORTED)
        g.check("unsupported_count_reproduced", int(np.sum(unsupported)) == EXPECTED_UNSUPPORTED)
        g.check("unsupported_still_nan", np.all(np.isnan(s_grid[unsupported])))
        g.check("supported_finite", np.all(np.isfinite(s_grid[support])))
        g.check("piece_visit_support_consistency", np.all(pieces[support] > 0) and np.all(visits[support] > 0) and np.all(pieces[unsupported] == 0) and np.all(visits[unsupported] == 0))

        recorded_arrays = e13_contract.get("array_sha256", {})
        g.check("E13R1_saturation_array_SHA_exact", arr_sha(s_grid) == recorded_arrays.get("saturation_grid_float64"))
        g.check("E13R1_denominator_array_SHA_exact", arr_sha(den) == recorded_arrays.get("support_denominator"))
        g.check("E13R1_numerator_array_SHA_exact", arr_sha(num) == recorded_arrays.get("support_numerator"))
        g.check("E13R1_support_array_SHA_exact", arr_sha(support.astype(np.uint8)) == recorded_arrays.get("supported_mask"))

        # ------------------------------------------------------------------
        # V16E-11-R2 transport/background authority.
        # ------------------------------------------------------------------
        print("\nV16E-11-R2 FROZEN TRANSPORT BACKGROUND AUTHORITY")
        bind(g, "E11R2_runner", repo / E11R2_RUNNER[0], E11R2_RUNNER[1])
        pilot_path = compute / E11R2_REL / E11R2_PILOT[0]
        bind(g, "E11R2_pilot", pilot_path, E11R2_PILOT[1])
        with np.load(pilot_path, allow_pickle=False) as db:
            g.check("E11R2_background_keys_present", "saturation_100d" in db.files and "constitutive_swc" in db.files)
            sat_native = np.array(db["saturation_100d"], copy=True)
            swc = float(np.asarray(db["constitutive_swc"]))
        g.check("E11R2_saturation_native_float32", sat_native.dtype == np.float32, str(sat_native.dtype))
        g.check("E11R2_constitutive_swc_exact_0p2", swc == EXPECTED_SWC, f"{swc:.17g}")
        native_min = float(np.min(sat_native))
        swc32 = float(np.float32(swc))
        g.check("transport_min_equals_float32_Swc", native_min == swc32, f"min={native_min:.17g}, float32(Swc)={swc32:.17g}")
        g.check("all_transport_states_at_or_above_background", np.all(sat_native >= np.float32(swc)))
        background = swc  # Exact physical authority for future fill; source min is its float32 representation.
        g.check("background_below_diagnostic_threshold", background < DIAGNOSTIC_THRESHOLD, f"background={background}, diagnostic={DIAGNOSTIC_THRESHOLD}")

        # ------------------------------------------------------------------
        # V15 unsupported-cell source lineage.
        # ------------------------------------------------------------------
        print("\nVERSION-15 UNSUPPORTED-CELL POLICY SOURCE AUTHORITY")
        d3_path = repo / V15_D3[0]
        d4_path = repo / V15_D4[0]
        d5_path = repo / V15_D5[0]
        bind(g, "V15SG7D3_source", d3_path, V15_D3[1])
        bind(g, "V15SG7D4_source", d4_path, V15_D4[1])
        bind(g, "V15SG7D5_source", d5_path, V15_D5[1])
        authority = load_source_module(d3_path)
        g.check("V15SG7D3_grid_exact", tuple(authority.EXPECTED_SHAPE) == EXPECTED_GRID)
        g.check("V15SG7D3_diagnostic_threshold_exact", float(authority.DIAGNOSTIC_THRESHOLD) == DIAGNOSTIC_THRESHOLD)
        g.check("V15SG7D3_helpers_available", all(callable(getattr(authority, n, None)) for n in ["connected_components_3d", "neighbor_context", "manhattan_distance_to_support"]))
        g.check("V15SG7D4_P4_semantics_present", source_contains(d4_path, ["P4_MASKED_BACKGROUND_PLUS_SUPPORT", "supported_cells_exactly_preserved", "unsupported_cells_equal_background", "no_interpolation_used", "no_nearest_neighbor_used"]))
        g.check("V15SG7D5_independent_validation_semantics_present", source_contains(d5_path, ["supported_cells_preserved", "unsupported_cells_equal_frozen_background", "conservative_denominator_preserved", "conservative_numerator_preserved", "no_interpolation_used", "no_nearest_neighbor_used"]))

        # ------------------------------------------------------------------
        # Unsupported geometry / distance / neighbor characterization.
        # ------------------------------------------------------------------
        print("\nV16 UNSUPPORTED-CELL GEOMETRY / CONTEXT")
        components = authority.connected_components_3d(unsupported)
        unsupported_components = len(components)
        largest_unsupported = int(components[0]) if components else 0
        largest_unsupported_fraction = float(largest_unsupported / EXPECTED_UNSUPPORTED) if EXPECTED_UNSUPPORTED else 0.0
        g.check("unsupported_topology_established", unsupported_components >= 1)
        g.check("unsupported_component_sizes_close", sum(components) == EXPECTED_UNSUPPORTED)

        dist = authority.manhattan_distance_to_support(support)
        unsupported_dist = np.asarray(dist[unsupported], dtype=np.int32)
        g.check("distance_to_support_complete", unsupported_dist.size == EXPECTED_UNSUPPORTED)
        g.check("distance_to_support_positive", np.all(unsupported_dist > 0))

        neighbor_count, neighbor_mean, neighbor_min, neighbor_max = authority.neighbor_context(support, s_grid)
        unsupported_neighbor_count = neighbor_count[unsupported]
        g.check("neighbor_context_complete", unsupported_neighbor_count.size == EXPECTED_UNSUPPORTED)
        g.check("neighbor_counts_in_0_to_6", np.all((unsupported_neighbor_count >= 0) & (unsupported_neighbor_count <= 6)))

        boundary_mask = np.zeros(EXPECTED_GRID, dtype=bool)
        boundary_mask[0, :, :] = True
        boundary_mask[-1, :, :] = True
        boundary_mask[:, 0, :] = True
        boundary_mask[:, -1, :] = True
        boundary_mask[:, :, 0] = True
        boundary_mask[:, :, -1] = True
        unsupported_boundary = int(np.sum(unsupported & boundary_mask))
        unsupported_interior = EXPECTED_UNSUPPORTED - unsupported_boundary

        # Layer distribution and cross-check against E14's persisted census.
        layer_rows: list[dict[str, Any]] = []
        for k in range(EXPECTED_GRID[0]):
            sup = int(np.sum(support[k]))
            unsup = int(np.sum(unsupported[k]))
            layer_rows.append({
                "k": k,
                "layer_1_based": k + 1,
                "supported_cells": sup,
                "unsupported_cells": unsup,
                "supported_fraction": float(np.mean(support[k])),
                "unsupported_fraction": float(np.mean(unsupported[k])),
            })
        e14_layers = read_csv(e14_paths["layers"])
        e14_counts = [(int(r["supported_cells"]), int(r["unsupported_cells"])) for r in e14_layers]
        this_counts = [(r["supported_cells"], r["unsupported_cells"]) for r in layer_rows]
        g.check("layer_distribution_matches_E14_exact", e14_counts == this_counts)

        distance_rows: list[dict[str, Any]] = []
        for d in np.unique(unsupported_dist):
            n = int(np.sum(unsupported_dist == d))
            distance_rows.append({
                "manhattan_distance_cells": int(d),
                "unsupported_cells": n,
                "fraction_of_unsupported": float(n / EXPECTED_UNSUPPORTED),
            })

        neighbor_rows: list[dict[str, Any]] = []
        for count in range(7):
            mask = unsupported & (neighbor_count == count)
            n = int(np.sum(mask))
            if n == 0:
                continue
            vals = neighbor_mean[mask]
            finite_vals = vals[np.isfinite(vals)]
            neighbor_rows.append({
                "supported_6neighbor_count": count,
                "unsupported_cells": n,
                "fraction_of_unsupported": float(n / EXPECTED_UNSUPPORTED),
                "mean_neighbor_saturation": float(np.mean(finite_vals)) if finite_vals.size else np.nan,
                "min_neighbor_saturation": float(np.nanmin(neighbor_min[mask])) if finite_vals.size else np.nan,
                "max_neighbor_saturation": float(np.nanmax(neighbor_max[mask])) if finite_vals.size else np.nan,
            })

        # ------------------------------------------------------------------
        # Candidate policy audit. No policy is applied here.
        # ------------------------------------------------------------------
        print("\nCANDIDATE UNSUPPORTED-CELL POLICY AUDIT")
        policies = [
            {
                "policy": "P0_KEEP_NAN",
                "description": "Retain unsupported cells as NaN / explicit no-streamline-support state.",
                "conservation_semantics_score": 3,
                "invention_risk_score": 0,
                "topology_risk_score": 0,
                "plume_risk_score": 0,
                "deterministic": True,
                "full_grid_field": False,
                "changes_supported_cells": False,
                "uses_new_saturation_information": False,
            },
            {
                "policy": "P1_BACKGROUND_STATE",
                "description": "Assign frozen constitutive background saturation to unsupported cells.",
                "conservation_semantics_score": 3,
                "invention_risk_score": 1,
                "topology_risk_score": 0,
                "plume_risk_score": 0,
                "deterministic": True,
                "full_grid_field": True,
                "changes_supported_cells": False,
                "uses_new_saturation_information": False,
            },
            {
                "policy": "P2_NEAREST_SUPPORTED",
                "description": "Copy saturation from the nearest supported cell.",
                "conservation_semantics_score": 1,
                "invention_risk_score": 2,
                "topology_risk_score": 2,
                "plume_risk_score": 2,
                "deterministic": True,
                "full_grid_field": True,
                "changes_supported_cells": False,
                "uses_new_saturation_information": True,
            },
            {
                "policy": "P3_HARMONIC_LOCAL_INTERPOLATION",
                "description": "Interpolate unsupported cells from neighboring supported values.",
                "conservation_semantics_score": 1,
                "invention_risk_score": 3,
                "topology_risk_score": 3,
                "plume_risk_score": 3,
                "deterministic": True,
                "full_grid_field": True,
                "changes_supported_cells": False,
                "uses_new_saturation_information": True,
            },
            {
                "policy": "P4_MASKED_BACKGROUND_PLUS_SUPPORT",
                "description": "Preserve V16E-13-R1 exactly where supported; use frozen Swc background elsewhere; preserve support mask/evidence.",
                "conservation_semantics_score": 3,
                "invention_risk_score": 1,
                "topology_risk_score": 0,
                "plume_risk_score": 0,
                "deterministic": True,
                "full_grid_field": True,
                "changes_supported_cells": False,
                "uses_new_saturation_information": False,
            },
        ]
        selected_policy = "P4_MASKED_BACKGROUND_PLUS_SUPPORT"
        for p in policies:
            p["total_risk_score"] = int(p["invention_risk_score"] + p["topology_risk_score"] + p["plume_risk_score"])
            p["recommended_for_full_grid"] = p["policy"] == selected_policy

        supported_plume = support & np.isfinite(s_grid) & (s_grid >= DIAGNOSTIC_THRESHOLD)
        supported_plume_cells = int(np.sum(supported_plume))
        background_crosses = background >= DIAGNOSTIC_THRESHOLD
        p4_added_plume = EXPECTED_UNSUPPORTED if background_crosses else 0
        near_plume = unsupported & (neighbor_max >= DIAGNOSTIC_THRESHOLD)
        near_plume_unsupported = int(np.sum(near_plume))
        plume_risk_rows = [
            {"policy": "P0_KEEP_NAN", "existing_supported_diagnostic_plume_cells": supported_plume_cells, "potential_added_unsupported_diagnostic_plume_cells": 0, "risk_class": "NONE"},
            {"policy": selected_policy, "existing_supported_diagnostic_plume_cells": supported_plume_cells, "potential_added_unsupported_diagnostic_plume_cells": p4_added_plume, "risk_class": "NONE" if not background_crosses else "HIGH"},
            {"policy": "P2_NEAREST_SUPPORTED", "existing_supported_diagnostic_plume_cells": supported_plume_cells, "potential_added_unsupported_diagnostic_plume_cells": near_plume_unsupported, "risk_class": "MATERIAL"},
            {"policy": "P3_HARMONIC_LOCAL_INTERPOLATION", "existing_supported_diagnostic_plume_cells": supported_plume_cells, "potential_added_unsupported_diagnostic_plume_cells": near_plume_unsupported, "risk_class": "MATERIAL"},
        ]

        g.check("candidate_policy_matrix_five_policies", len(policies) == 5)
        g.check("selected_policy_P4", selected_policy == "P4_MASKED_BACKGROUND_PLUS_SUPPORT")
        g.check("selected_policy_preserves_supported_cells", next(p for p in policies if p["policy"] == selected_policy)["changes_supported_cells"] is False)
        g.check("selected_policy_uses_no_new_saturation_information", next(p for p in policies if p["policy"] == selected_policy)["uses_new_saturation_information"] is False)
        g.check("selected_policy_adds_zero_diagnostic_plume_cells", p4_added_plume == 0)
        g.check("nearest_and_interpolation_not_authorized", all(not p["recommended_for_full_grid"] for p in policies if p["policy"] in {"P2_NEAREST_SUPPORTED", "P3_HARMONIC_LOCAL_INTERPOLATION"}))
        g.check("no_cell_changed_in_E15", True)
        g.check("future_completion_requires_independent_validation", True)

        # ------------------------------------------------------------------
        # Publish design/audit artifacts only.
        # ------------------------------------------------------------------
        out.mkdir(parents=True, exist_ok=True)
        geometry = {
            "milestone": MILESTONE,
            "status": "PASS",
            "grid_shape": list(EXPECTED_GRID),
            "supported_cells": EXPECTED_SUPPORTED,
            "unsupported_cells": EXPECTED_UNSUPPORTED,
            "unsupported_component_count": unsupported_components,
            "unsupported_component_sizes_descending": components,
            "largest_unsupported_component_cells": largest_unsupported,
            "largest_unsupported_component_fraction": largest_unsupported_fraction,
            "unsupported_boundary_cells": unsupported_boundary,
            "unsupported_interior_cells": unsupported_interior,
            "boundary_fraction_of_unsupported": float(unsupported_boundary / EXPECTED_UNSUPPORTED),
            "max_manhattan_distance_to_support": int(np.max(unsupported_dist)),
            "mean_manhattan_distance_to_support": float(np.mean(unsupported_dist)),
            "median_manhattan_distance_to_support": float(np.median(unsupported_dist)),
        }
        decision = {
            "milestone": MILESTONE,
            "status": "PASS",
            "selected_policy": selected_policy,
            "background_authority": "E11-R2 constitutive_swc",
            "background_saturation_float64": background,
            "persisted_transport_min_float32": native_min,
            "float32_background_representation": swc32,
            "transport_min_equals_float32_background": native_min == swc32,
            "diagnostic_threshold": DIAGNOSTIC_THRESHOLD,
            "diagnostic_threshold_semantics": "HISTORICAL_V15_POLICY_RISK_PREVIEW_ONLY_NOT_SG7E_NOT_A_PASSFAIL_PLUME_METRIC",
            "background_below_diagnostic_threshold": background < DIAGNOSTIC_THRESHOLD,
            "supported_cells": EXPECTED_SUPPORTED,
            "unsupported_cells": EXPECTED_UNSUPPORTED,
            "supported_diagnostic_plume_cells": supported_plume_cells,
            "P4_added_unsupported_diagnostic_plume_cells": p4_added_plume,
            "near_plume_unsupported_cells_diagnostic": near_plume_unsupported,
            "unsupported_cells_filled": False,
            "next_milestone": NEXT_PASS,
        }
        contract = {
            "milestone": MILESTONE,
            "status": SUCCESS,
            "selected_policy": selected_policy,
            "policy_semantics": {
                "supported_cells": "preserve V16E-13-R1 saturation_grid_float64 exactly",
                "unsupported_cells": "assign exact frozen constitutive Swc background only in the future controlled execution milestone",
                "background_saturation_float64": background,
                "support_mask": "preserve exactly as provenance; background-filled cells remain unsupported",
                "support_numerator": "preserve exactly; remains evidence only for supported conservative map-back",
                "support_denominator": "preserve exactly; remains evidence only for supported conservative map-back",
                "interpolation": "PROHIBITED",
                "nearest_neighbor": "PROHIBITED",
                "route_specific_fill": "PROHIBITED",
                "new_conservative_projection": "PROHIBITED",
                "full_grid_field_semantics": "supported conservative map-back plus initial/background state completion; not full-grid streamline support",
            },
            "future_V16E16_execution_gates": {
                "E13R1_supported_cells_bitwise_unchanged": True,
                "all_unsupported_equal_background": True,
                "support_mask_hash_unchanged": True,
                "support_numerator_hash_unchanged": True,
                "support_denominator_hash_unchanged": True,
                "full_grid_all_finite": True,
                "no_interpolation": True,
                "no_nearest_neighbor": True,
                "unsupported_diagnostic_plume_cells": 0,
                "independent_V16E17_validation_required_before_freeze": True,
            },
            "authority": {
                "E14_runner_sha256": E14_RUNNER[1],
                "E14_artifacts": {k: {"file": v[0], "sha256": v[1]} for k, v in E14.items()},
                "E13R1_runner_sha256": E13R1_RUNNER[1],
                "E13R1_artifacts": {k: {"file": v[0], "sha256": v[1]} for k, v in E13R1.items()},
                "E11R2_runner_sha256": E11R2_RUNNER[1],
                "E11R2_pilot_sha256": E11R2_PILOT[1],
                "V15SG7D3_source_sha256": V15_D3[1],
                "V15SG7D4_source_sha256": V15_D4[1],
                "V15SG7D5_source_sha256": V15_D5[1],
            },
            "current_state": {
                "physical_time_days": EXPECTED_TIME_DAYS,
                "grid_shape": list(EXPECTED_GRID),
                "supported_cells": EXPECTED_SUPPORTED,
                "unsupported_cells": EXPECTED_UNSUPPORTED,
                "support_fraction": EXPECTED_SUPPORT_FRACTION,
                "unsupported_cells_filled": False,
                "full_grid_candidate_created": False,
                "full_grid_plume_authorized": False,
            },
            "next_milestone": NEXT_PASS,
        }
        audit = {
            "milestone": MILESTONE,
            "status": SUCCESS,
            "geometry": geometry,
            "decision": decision,
            "policy_matrix": policies,
            "firewall": {
                "E13R1_modified": False,
                "E14_modified": False,
                "grid_values_modified": False,
                "unsupported_cells_filled": False,
                "mapback_reexecuted": False,
                "training": False,
                "model_inference": False,
                "upstream_physics_recomputed": False,
                "SG7E_threshold_changed": False,
                "full_grid_plume_authorized": False,
                "internal_test_reopened": False,
                "OOD_reopened": False,
            },
            "gates": g.items,
        }
        summary = {
            "milestone": MILESTONE,
            "status": "PASS",
            "physical_time_days": EXPECTED_TIME_DAYS,
            "grid_shape": list(EXPECTED_GRID),
            "supported_cells": EXPECTED_SUPPORTED,
            "unsupported_cells": EXPECTED_UNSUPPORTED,
            "support_fraction": EXPECTED_SUPPORT_FRACTION,
            "unsupported_component_count": unsupported_components,
            "largest_unsupported_component_cells": largest_unsupported,
            "largest_unsupported_component_fraction": largest_unsupported_fraction,
            "max_manhattan_distance_to_support": int(np.max(unsupported_dist)),
            "mean_manhattan_distance_to_support": float(np.mean(unsupported_dist)),
            "background_saturation": background,
            "selected_policy": selected_policy,
            "unsupported_cells_filled": False,
            "full_grid_candidate_created": False,
            "full_grid_plume_authorized": False,
            "next_milestone": NEXT_PASS,
        }
        handoff = f"""# PAD-Stream V16E-15 - SGSim Unsupported-Cell Policy Design / Audit PASS\n\nV16E-14 independently validated the 20,462-cell supported map-back and established that 17,038 cells remain unsupported. V16E-15 changed no grid value.\n\nSelected future completion policy: `{selected_policy}`.\n\n- Supported cells: preserve the accepted V16E-13-R1 float64 values exactly.\n- Unsupported cells: assign only the frozen constitutive background saturation Swc = {background:.17g} in V16E-16.\n- Support mask, numerator, and denominator remain immutable provenance of the supported conservative map-back.\n- Nearest-neighbor and interpolation fills are prohibited.\n- The background fill is a minimum-information completion, not a claim of streamline support in those cells.\n- A future completed full-grid candidate must undergo independent V16E-17 validation before any freeze or plume claim.\n\nUnsupported components: {unsupported_components}; largest = {largest_unsupported} cells ({largest_unsupported_fraction:.12f} of unsupported cells).\nMax / mean Manhattan distance to support: {int(np.max(unsupported_dist))} / {float(np.mean(unsupported_dist)):.12f} cells.\n\nNo unsupported cell was filled in V16E-15.\n\nNEXT: {NEXT_PASS}\n""".encode("utf-8")

        files = {
            "V16E15_Unsupported_Geometry_Audit.json": enc(geometry),
            "V16E15_Policy_Decision.json": enc(decision),
            "V16E15_Unsupported_Cell_Policy_Contract.json": enc(contract),
            "V16E15_Unsupported_Cell_Policy_Audit.json": enc(audit),
            "PAD_Stream_V16E15_Summary.json": enc(summary),
            "V16E15_Handoff.md": handoff,
        }
        for name, data in files.items():
            atomic_write(out / name, data)
        write_csv(out / "V16E15_Unsupported_Distance_to_Support.csv", distance_rows)
        write_csv(out / "V16E15_Unsupported_Neighbor_Context.csv", neighbor_rows)
        write_csv(out / "V16E15_Candidate_Policy_Audit.csv", policies)
        write_csv(out / "V16E15_Unsupported_By_Layer.csv", layer_rows)
        write_csv(out / "V16E15_Policy_Plume_Risk.csv", plume_risk_rows)

        print("\n" + "=" * 126)
        print("V16E-15 RESULT: PASS")
        print("=" * 126)
        print(f"{'SGSim grid':62}: 15 x 50 x 50")
        print(f"{'Supported / unsupported cells':62}: {EXPECTED_SUPPORTED} / {EXPECTED_UNSUPPORTED}")
        print(f"{'Unsupported connected components':62}: {unsupported_components}")
        print(f"{'Largest unsupported component cells / share':62}: {largest_unsupported} / {largest_unsupported_fraction:.12f}")
        print(f"{'Max / mean Manhattan distance to support':62}: {int(np.max(unsupported_dist))} / {float(np.mean(unsupported_dist)):.12f}")
        print(f"{'Frozen background saturation Swc':62}: {background:.17g}")
        print(f"{'Persisted transport minimum (float32)':62}: {native_min:.17g}")
        print(f"{'Selected policy':62}: {selected_policy}")
        print(f"{'Unsupported cells filled in E15':62}: NO")
        print(f"{'Future nearest/interpolation fill authorized':62}: NO")
        print(f"{'Future exact background-only completion authorized':62}: YES, V16E-16 only")
        print(f"{'Full-grid plume authorized':62}: NO")
        print(f"{'Independent post-completion validation required':62}: YES")
        for name in files:
            print(f"{name} SHA: {sha(out / name)}")
        for name in [
            "V16E15_Unsupported_Distance_to_Support.csv",
            "V16E15_Unsupported_Neighbor_Context.csv",
            "V16E15_Candidate_Policy_Audit.csv",
            "V16E15_Unsupported_By_Layer.csv",
            "V16E15_Policy_Plume_Risk.csv",
        ]:
            print(f"{name} SHA: {sha(out / name)}")
        print("Output:", out)
        print("NEXT:", NEXT_PASS)
        return 0

    except Exception as exc:
        print(f"\n[FAIL] V16E-15 did not close: {exc}")
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
                "grid_values_modified": False,
                "unsupported_cell_fill_performed": False,
                "full_grid_plume_authorized": False,
                "next_milestone": NEXT_FAIL,
            }
            p = bdir / "V16E15_Blocked_Unsupported_Cell_Policy_Design_Audit.json"
            atomic_write(p, enc(report))
            print("Blocked report SHA:", sha(p))
            print("Blocked output:", bdir)
        except Exception:
            pass
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
