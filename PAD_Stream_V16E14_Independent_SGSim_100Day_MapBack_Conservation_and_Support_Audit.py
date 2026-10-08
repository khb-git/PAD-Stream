#!/usr/bin/env python3
"""PAD-Stream V16E-14
Independent SGSim 100-Day Map-Back Conservation / Support Audit.

This is a diagnostic-only audit of the accepted V16E-13-R1 supported-cell
map-back. It does not rerun streamline-to-grid deposition, alter the mapped
field, fill unsupported cells, threshold a plume, load a neural model, or
recompute upstream flow/transport physics.

The audit is source-bound to the V15-SG7D2 independent-audit semantics frozen
by V16E-12-R1. It independently reconstructs the supported-cell saturation
from the persisted numerator/denominator, recomputes global conservation from
the persisted accumulators, audits support topology/layer distribution, and
decides whether an unsupported-cell policy is required before any full-grid
claim.
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

MILESTONE = "V16E-14"
SUCCESS = "V16E14_INDEPENDENT_SGSIM_100D_MAPBACK_CONSERVATION_SUPPORT_AUDIT_PASS"
BLOCKED = "V16E14_INDEPENDENT_SGSIM_100D_MAPBACK_CONSERVATION_SUPPORT_AUDIT_BLOCKED"
NEXT_PASS = "V16E-15 - SGSim Unsupported-Cell Policy Design / Audit"
NEXT_FAIL = "V16E-14-R1 - Repair only the failed independent-audit gate; preserve E13-R1 unchanged"

E13R1_RUNNER = (
    "PAD_Stream_V16E13_R1_Native_Dtype_Identity_Repair_and_Controlled_Conservative_Streamline_to_Grid_MapBack_Execution.py",
    "b8e04c2db9846709c2791afa65d8b10fd9b9e8ada0ac48b0b24cbdf4765e80b6",
)
E13R1_REL = Path("pilots/hybrid_dp/V16E13_R1_SGSIM_100D_CONTROLLED_CONSERVATIVE_MAPBACK")
E13R1 = {
    "numerical": (
        "V16E13_R1_SGSim_100Day_Conservative_MapBack.npz",
        "6ef79d6f126a96b7e64a5fb7f9d11164758b9c2726657ff4f7874f0e6acfa79f",
    ),
    "audit": (
        "V16E13_R1_Conservative_MapBack_Audit.json",
        "934dc12405450dfef10ca177d617a52a91db50b7f5deefd179ef0064bdb5e6cb",
    ),
    "contract": (
        "V16E13_R1_Conservative_MapBack_Contract.json",
        "733ced4bb7da6b3c808871f36f73634cd5d3da2290cdde3ca099321fb871a048",
    ),
    "summary": (
        "PAD_Stream_V16E13_R1_Summary.json",
        "e6000730fbcb5c97e922033e48f215b00719816f7fb3a7e90474a6631f4d27a5",
    ),
    "handoff": (
        "V16E13_R1_Handoff.md",
        "57fcc84032c7fbb7089a265e7162e050264db4cde1b748744043691e80f3eb51",
    ),
}

E12R1_RUNNER = (
    "PAD_Stream_V16E12_R1_Route_Semantics_Reconciliation_and_Conservative_MapBack_Protocol_Freeze.py",
    "fdd4c3ad5488fbe90d9d35764608363265b6c0831835e517ea3bdc4aec716971",
)
E12R1_REL = Path("provenance/hybrid_dp/V16E12_R1_ROUTE_SEMANTICS_RECONCILED_PILOT_EVIDENCE_AND_MAPBACK_PROTOCOL_FREEZE")
E12R1_PROTOCOL = (
    "V16E12_R1_Conservative_MapBack_Protocol.json",
    "71da16ef29f643858539505dc3a139b86b20ba92ebde3f82ecb810845a85bb69",
)

AUDIT_SOURCE = "PAD_Stream_V15SG7D2_Independent_MapBack_Conservation_Support_Audit.py"
OUT_REL = Path("provenance/hybrid_dp/V16E14_INDEPENDENT_SGSIM_100D_MAPBACK_CONSERVATION_SUPPORT_AUDIT")
BLOCKED_REL = Path("provenance/hybrid_dp/V16E14_BLOCKED_INDEPENDENT_MAPBACK_AUDIT")

EXPECTED_GRID = (15, 50, 50)
EXPECTED_CELLS = 37500
EXPECTED_SUPPORTED = 20462
EXPECTED_UNSUPPORTED = 17038
EXPECTED_SUPPORT_FRACTION = 0.5456533333333333
EXPECTED_TIME_DAYS = 100.0

PROHIBITIONS = [
    "NO CHANGE TO V16E-13-R1 ARTIFACTS OR GRID ARRAYS.",
    "NO STREAMLINE-TO-GRID DEPOSITION RE-EXECUTION.",
    "NO TRAINING, CHECKPOINT LOAD, OR MODEL INFERENCE.",
    "NO PRESSURE / DARCY / POLLOCK / TOF RECOMPUTATION.",
    "NO UNSUPPORTED-CELL FILL, INTERPOLATION, OR BACKGROUND COMPLETION.",
    "NO GLOBAL FULL-GRID CONSERVATIVE PROJECTION.",
    "NO SG7E OR OTHER PLUME THRESHOLDING.",
    "NO FULL-GRID PLUME CLAIM.",
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


def bind(g: Gates, label: str, path: Path, expected: str) -> str:
    g.check(label + "_exists", path.is_file(), str(path))
    actual = sha(path)
    g.check(label + "_SHA_exact", actual == expected, actual if actual != expected else "")
    return actual


def load_source_module(path: Path):
    spec = importlib.util.spec_from_file_location("v15_sg7d2_audit_authority", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not construct V15-SG7D2 import specification")
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
        for k in row:
            if k not in fields:
                fields.append(k)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, path)


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
    print("PAD-Stream V16E-14 Independent SGSim 100-Day Map-Back Conservation / Support Audit")
    print("=" * 126)
    for x in PROHIBITIONS:
        print(x)

    try:
        # ------------------------------------------------------------------
        # Parent / protocol authority.
        # ------------------------------------------------------------------
        print("\nV16E-13-R1 ACCEPTED MAP-BACK AUTHORITY")
        bind(g, "E13R1_runner", repo / E13R1_RUNNER[0], E13R1_RUNNER[1])
        parent_paths: dict[str, Path] = {}
        for key, (fn, hs) in E13R1.items():
            p = compute / E13R1_REL / fn
            bind(g, "E13R1_" + key, p, hs)
            parent_paths[key] = p

        e13_audit = read_json(parent_paths["audit"])
        e13_contract = read_json(parent_paths["contract"])
        e13_summary = read_json(parent_paths["summary"])
        g.check("E13R1_status_PASS", e13_summary.get("status") == "PASS")
        g.check("E13R1_physical_time_100d", float(e13_summary.get("physical_time_days")) == EXPECTED_TIME_DAYS)
        g.check("E13R1_grid_shape_exact", tuple(e13_summary.get("grid_shape", [])) == EXPECTED_GRID)
        g.check("E13R1_supported_count_exact", int(e13_summary.get("supported_cells")) == EXPECTED_SUPPORTED)
        g.check("E13R1_unsupported_count_exact", int(e13_summary.get("unsupported_cells")) == EXPECTED_UNSUPPORTED)
        g.check("E13R1_support_fraction_exact", float(e13_summary.get("support_fraction")) == EXPECTED_SUPPORT_FRACTION)
        g.check("E13R1_deterministic_repeat_exact", e13_summary.get("deterministic_repeat_exact") is True)
        g.check("E13R1_unsupported_not_filled", e13_summary.get("unsupported_cells_filled") is False)
        g.check("E13R1_full_grid_not_authorized", e13_summary.get("full_grid_plume_authorized") is False)
        g.check("E13R1_no_test_OOD", e13_summary.get("internal_test_reopened") is False and e13_summary.get("OOD_reopened") is False)
        g.check("E13R1_contract_requires_independent_audit", e13_contract.get("independent_V16_audit_required") is True)
        g.check("E13R1_contract_supported_candidate_only", e13_contract.get("supported_cell_field_is_candidate") is True)
        g.check("E13R1_contract_unsupported_nan", e13_contract.get("unsupported_cells_remain_nan") is True)
        g.check("E13R1_audit_no_upstream_recompute", e13_audit.get("firewall", {}).get("pressure_Darcy_Pollock_TOF_recomputed") is False)

        print("\nV16E-12-R1 FROZEN AUDIT PROTOCOL AUTHORITY")
        bind(g, "E12R1_runner", repo / E12R1_RUNNER[0], E12R1_RUNNER[1])
        protocol_path = compute / E12R1_REL / E12R1_PROTOCOL[0]
        bind(g, "E12R1_protocol", protocol_path, E12R1_PROTOCOL[1])
        protocol = read_json(protocol_path)
        g.check("E12R1_closure_limit_1e8", float(protocol["operator_contract"]["support_closure_relative_max"]) == 1e-8 and float(protocol["operator_contract"]["saturation_measure_closure_relative_max"]) == 1e-8)
        g.check("E12R1_unsupported_state_nan", protocol["operator_contract"]["unsupported_cell_state"] == "NaN")
        g.check("E12R1_no_fill_authority", protocol["operator_contract"]["unsupported_fill_authorized"] is False)
        g.check("E12R1_post_mapback_independent_audit_required", "Independent" in protocol.get("post_E13_required_audit", ""))

        source_path = repo / AUDIT_SOURCE
        g.check("V15SG7D2_source_exists", source_path.is_file(), str(source_path))
        recorded_source = protocol["frozen_mapback_source_lineage"][AUDIT_SOURCE]["sha256"]
        source_actual = sha(source_path)
        g.check("V15SG7D2_source_SHA_matches_E12R1", source_actual == recorded_source, source_actual if source_actual != recorded_source else "")
        authority = load_source_module(source_path)
        g.check("V15SG7D2_expected_grid_exact", tuple(authority.EXPECTED_SHAPE) == EXPECTED_GRID)
        g.check("V15SG7D2_support_closure_limit_exact", float(authority.SUPPORT_CLOSURE_LIMIT) == 1e-8)
        g.check("V15SG7D2_sat_measure_closure_limit_exact", float(authority.SAT_MEASURE_CLOSURE_LIMIT) == 1e-8)
        g.check("V15SG7D2_connected_components_available", callable(getattr(authority, "connected_components_3d", None)))

        # ------------------------------------------------------------------
        # Independent artifact-level reconstruction.
        # ------------------------------------------------------------------
        print("\nINDEPENDENT NUMERICAL ARTIFACT AUDIT")
        npz_path = parent_paths["numerical"]
        required = [
            "saturation_grid", "saturation_grid_float64", "support_denominator",
            "support_numerator", "supported_mask", "segment_piece_count",
            "streamline_visit_count", "grid_shape", "cell_size_m", "domain_size_m",
            "physical_time_days", "total_input_weighted_length",
            "total_deposited_weighted_length", "total_input_weighted_sat_length",
            "total_deposited_weighted_sat_length",
        ]
        with np.load(npz_path, allow_pickle=False) as db:
            g.check("numerical_required_keys_present", all(k in db.files for k in required), str(db.files))
            s32 = np.array(db["saturation_grid"], copy=True)
            s64 = np.array(db["saturation_grid_float64"], copy=True)
            den = np.array(db["support_denominator"], dtype=np.float64, copy=True)
            num = np.array(db["support_numerator"], dtype=np.float64, copy=True)
            mask_stored = np.array(db["supported_mask"], copy=True).astype(bool)
            pieces = np.array(db["segment_piece_count"], dtype=np.int64, copy=True)
            visits = np.array(db["streamline_visit_count"], dtype=np.int64, copy=True)
            grid_shape = tuple(int(v) for v in np.asarray(db["grid_shape"]).tolist())
            physical_time = float(np.asarray(db["physical_time_days"]))
            input_support = float(np.asarray(db["total_input_weighted_length"]))
            deposited_support = float(np.asarray(db["total_deposited_weighted_length"]))
            input_sat = float(np.asarray(db["total_input_weighted_sat_length"]))
            deposited_sat = float(np.asarray(db["total_deposited_weighted_sat_length"]))

        g.check("numerical_grid_shape_exact", grid_shape == EXPECTED_GRID)
        g.check("numerical_physical_time_100d", physical_time == EXPECTED_TIME_DAYS)
        g.check("numerical_array_shapes_exact", all(a.shape == EXPECTED_GRID for a in [s32, s64, den, num, mask_stored, pieces, visits]))

        # Exact array identities recorded by E13-R1 itself.
        recorded_arrays = e13_contract["array_sha256"]
        array_actual = {
            "saturation_grid_float64": arr_sha(s64),
            "support_denominator": arr_sha(den),
            "support_numerator": arr_sha(num),
            "supported_mask": arr_sha(mask_stored.astype(np.uint8)),
            "segment_piece_count": arr_sha(pieces),
            "streamline_visit_count": arr_sha(visits),
        }
        for key, actual in array_actual.items():
            g.check("E13R1_array_SHA_exact_" + key, actual == recorded_arrays[key])

        mask_rebuilt = den > 0.0
        g.check("support_mask_exact_from_denominator", np.array_equal(mask_rebuilt, mask_stored))
        supported_cells = int(np.sum(mask_rebuilt))
        unsupported_cells = int(mask_rebuilt.size - supported_cells)
        support_fraction = float(np.mean(mask_rebuilt))
        g.check("independent_supported_count_matches_parent", supported_cells == EXPECTED_SUPPORTED, str(supported_cells))
        g.check("independent_unsupported_count_matches_parent", unsupported_cells == EXPECTED_UNSUPPORTED, str(unsupported_cells))
        g.check("independent_support_fraction_matches_parent", support_fraction == EXPECTED_SUPPORT_FRACTION, f"{support_fraction:.16g}")

        reconstructed = np.full(EXPECTED_GRID, np.nan, dtype=np.float64)
        reconstructed[mask_rebuilt] = num[mask_rebuilt] / den[mask_rebuilt]
        delta = reconstructed[mask_rebuilt] - s64[mask_rebuilt]
        state_l1 = float(np.mean(np.abs(delta))) if supported_cells else float("nan")
        state_linf = float(np.max(np.abs(delta))) if supported_cells else float("nan")
        reconstructed_exact = bool(np.array_equal(reconstructed[mask_rebuilt], s64[mask_rebuilt]))

        g.check("unsupported_cells_remain_nan_float64", np.all(np.isnan(s64[~mask_rebuilt])))
        g.check("unsupported_cells_remain_nan_float32", np.all(np.isnan(s32[~mask_rebuilt])))
        g.check("supported_float64_finite", np.all(np.isfinite(s64[mask_rebuilt])))
        g.check("supported_float32_finite", np.all(np.isfinite(s32[mask_rebuilt])))
        g.check("numerator_denominator_reconstructs_state", np.isfinite(state_linf) and state_linf <= 1e-6, f"L1={state_l1:.12e}, Linf={state_linf:.12e}")
        g.check("float32_alias_matches_float64_cast", np.array_equal(s32, s64.astype(np.float32), equal_nan=True))

        # ------------------------------------------------------------------
        # Independent global conservation from the persisted accumulators.
        # ------------------------------------------------------------------
        print("\nINDEPENDENT GLOBAL CONSERVATION")
        eps = float(getattr(authority, "EPS", 1e-15))
        den_sum = float(np.sum(den))
        num_sum = float(np.sum(num))
        support_rel_source = abs(deposited_support - input_support) / max(abs(input_support), eps)
        support_rel_grid = abs(den_sum - input_support) / max(abs(input_support), eps)
        sat_rel_source = abs(deposited_sat - input_sat) / max(abs(input_sat), eps)
        sat_rel_grid = abs(num_sum - input_sat) / max(abs(input_sat), eps)

        g.check("persisted_support_closure_le_1e8", support_rel_source <= 1e-8, f"{support_rel_source:.12e}")
        g.check("independent_grid_support_closure_le_1e8", support_rel_grid <= 1e-8, f"{support_rel_grid:.12e}")
        g.check("persisted_sat_measure_closure_le_1e8", sat_rel_source <= 1e-8, f"{sat_rel_source:.12e}")
        g.check("independent_grid_sat_measure_closure_le_1e8", sat_rel_grid <= 1e-8, f"{sat_rel_grid:.12e}")
        g.check("piece_counts_nonnegative", np.all(pieces >= 0))
        g.check("visit_counts_nonnegative", np.all(visits >= 0))
        g.check("supported_cells_have_positive_piece_count", np.all(pieces[mask_rebuilt] > 0))
        g.check("supported_cells_have_positive_visit_count", np.all(visits[mask_rebuilt] > 0))
        g.check("unsupported_cells_have_zero_piece_count", np.all(pieces[~mask_rebuilt] == 0))
        g.check("unsupported_cells_have_zero_visit_count", np.all(visits[~mask_rebuilt] == 0))

        # ------------------------------------------------------------------
        # Support distribution / topology. No saturation threshold is used.
        # ------------------------------------------------------------------
        print("\nSUPPORT DISTRIBUTION / TOPOLOGY")
        layer_rows: list[dict[str, Any]] = []
        for k in range(EXPECTED_GRID[0]):
            sup = int(np.sum(mask_rebuilt[k]))
            unsup = int(mask_rebuilt[k].size - sup)
            layer_rows.append({
                "k": k,
                "layer_1_based": k + 1,
                "supported_cells": sup,
                "unsupported_cells": unsup,
                "support_fraction": float(np.mean(mask_rebuilt[k])),
                "denominator_sum": float(np.sum(den[k])),
                "numerator_sum": float(np.sum(num[k])),
            })
        g.check("layer_distribution_complete_15", len(layer_rows) == EXPECTED_GRID[0])
        g.check("layer_supported_sum_exact", sum(r["supported_cells"] for r in layer_rows) == supported_cells)
        g.check("layer_unsupported_sum_exact", sum(r["unsupported_cells"] for r in layer_rows) == unsupported_cells)

        components = authority.connected_components_3d(mask_rebuilt)
        component_count = len(components)
        largest_component = int(components[0]) if components else 0
        largest_fraction = float(largest_component / supported_cells) if supported_cells else 0.0
        g.check("support_topology_established", component_count >= 1)
        g.check("largest_component_valid", 0 < largest_component <= supported_cells)

        unsupported_policy_needed = unsupported_cells > 0
        g.check("unsupported_policy_required_before_full_grid", unsupported_policy_needed)
        g.check("no_full_grid_claim", e13_summary.get("full_grid_plume_authorized") is False)

        # ------------------------------------------------------------------
        # Publish audit-only artifacts.
        # ------------------------------------------------------------------
        out.mkdir(parents=True, exist_ok=True)
        layer_path = out / "V16E14_Support_By_Layer.csv"
        write_csv(layer_path, layer_rows)

        closure = {
            "milestone": MILESTONE,
            "status": "PASS",
            "state_reconstruction": {
                "supported_exact_bitwise": reconstructed_exact,
                "L1": state_l1,
                "Linf": state_linf,
                "V15SG7D2_acceptance_Linf_max": 1e-6,
            },
            "support": {
                "input_weighted_length": input_support,
                "persisted_deposited_weighted_length": deposited_support,
                "independent_denominator_sum": den_sum,
                "persisted_relative_error": support_rel_source,
                "independent_grid_relative_error": support_rel_grid,
                "acceptance_max": 1e-8,
            },
            "saturation_measure": {
                "input_weighted_sat_length": input_sat,
                "persisted_deposited_weighted_sat_length": deposited_sat,
                "independent_numerator_sum": num_sum,
                "persisted_relative_error": sat_rel_source,
                "independent_grid_relative_error": sat_rel_grid,
                "acceptance_max": 1e-8,
            },
        }
        topology = {
            "milestone": MILESTONE,
            "status": "PASS",
            "grid_shape": list(EXPECTED_GRID),
            "supported_cells": supported_cells,
            "unsupported_cells": unsupported_cells,
            "support_fraction": support_fraction,
            "support_component_count": component_count,
            "component_sizes_descending": components,
            "largest_component_cells": largest_component,
            "largest_component_fraction_of_supported": largest_fraction,
            "unsupported_policy_needed": unsupported_policy_needed,
            "saturation_threshold_used": False,
            "full_grid_plume_authorized": False,
        }
        audit = {
            "milestone": MILESTONE,
            "status": SUCCESS,
            "authority": {
                "E13R1_runner_sha256": E13R1_RUNNER[1],
                "E13R1_artifacts": {k: {"file": v[0], "sha256": v[1]} for k, v in E13R1.items()},
                "E12R1_runner_sha256": E12R1_RUNNER[1],
                "E12R1_protocol_sha256": E12R1_PROTOCOL[1],
                "V15SG7D2_source_sha256": source_actual,
            },
            "independent_results": {
                "physical_time_days": physical_time,
                "grid_shape": list(EXPECTED_GRID),
                "supported_cells": supported_cells,
                "unsupported_cells": unsupported_cells,
                "support_fraction": support_fraction,
                "state_reconstruction_L1": state_l1,
                "state_reconstruction_Linf": state_linf,
                "state_reconstruction_bitwise_exact": reconstructed_exact,
                "independent_support_closure_rel": support_rel_grid,
                "independent_sat_measure_closure_rel": sat_rel_grid,
                "support_component_count": component_count,
                "largest_support_component_cells": largest_component,
                "largest_support_component_fraction": largest_fraction,
            },
            "decision": {
                "E13R1_supported_cell_candidate_independently_validated": True,
                "unsupported_policy_needed": unsupported_policy_needed,
                "unsupported_fill_authorized": False,
                "full_grid_projection_authorized": False,
                "full_grid_plume_authorized": False,
                "next_milestone": NEXT_PASS,
            },
            "firewall": {
                "mapback_reexecuted": False,
                "training": False,
                "model_inference": False,
                "upstream_physics_recomputed": False,
                "unsupported_cells_filled": False,
                "plume_thresholding": False,
                "internal_test_reopened": False,
                "OOD_reopened": False,
            },
            "gates": g.items,
        }
        summary = {
            "milestone": MILESTONE,
            "status": "PASS",
            "physical_time_days": physical_time,
            "grid_shape": list(EXPECTED_GRID),
            "supported_cells": supported_cells,
            "unsupported_cells": unsupported_cells,
            "support_fraction": support_fraction,
            "independent_support_closure_rel": support_rel_grid,
            "independent_sat_measure_closure_rel": sat_rel_grid,
            "state_reconstruction_Linf": state_linf,
            "support_component_count": component_count,
            "largest_support_component_cells": largest_component,
            "largest_support_component_fraction": largest_fraction,
            "unsupported_policy_needed": unsupported_policy_needed,
            "unsupported_cells_filled": False,
            "full_grid_plume_authorized": False,
            "next_milestone": NEXT_PASS,
        }
        handoff = f"""# PAD-Stream V16E-14 - Independent SGSim 100-Day Map-Back Conservation / Support Audit PASS\n\nV16E-13-R1's supported-cell 100-day SGSim map-back was independently audited without rerunning the deposition operator or changing any parent array. The support mask was reconstructed from the persisted denominator, supported-cell saturation was independently reconstructed from numerator/denominator, and global support plus saturation-measure conservation were recomputed from the persisted accumulators.\n\nSupported cells: {supported_cells}\nUnsupported cells: {unsupported_cells}\nSupport fraction: {support_fraction:.12f}\nIndependent support closure rel: {support_rel_grid:.12e}\nIndependent saturation-measure closure rel: {sat_rel_grid:.12e}\nSupport connected components: {component_count}\nLargest component: {largest_component} cells ({largest_fraction:.12f} of supported cells)\n\nBecause unsupported cells remain, no full-grid plume is authorized. No unsupported-cell fill was performed. The next milestone may design and audit an explicit unsupported-cell policy, but it may not silently invent plume saturation or alter the accepted E13-R1 supported-cell values.\n\nNEXT: {NEXT_PASS}\n""".encode("utf-8")

        files = {
            "V16E14_Independent_MapBack_Audit.json": enc(audit),
            "V16E14_Independent_Closure_Audit.json": enc(closure),
            "V16E14_Support_Topology.json": enc(topology),
            "PAD_Stream_V16E14_Summary.json": enc(summary),
            "V16E14_Handoff.md": handoff,
        }
        for name, data in files.items():
            atomic_write(out / name, data)

        print("\n" + "=" * 126)
        print("V16E-14 RESULT: PASS")
        print("=" * 126)
        print(f"{'SGSim grid':58}: 15 x 50 x 50")
        print(f"{'Supported / unsupported cells':58}: {supported_cells} / {unsupported_cells}")
        print(f"{'Support fraction':58}: {support_fraction:.12f}")
        print(f"{'State reconstruction L1 / Linf':58}: {state_l1:.12e} / {state_linf:.12e}")
        print(f"{'Independent support closure relative':58}: {support_rel_grid:.12e}")
        print(f"{'Independent saturation-measure closure relative':58}: {sat_rel_grid:.12e}")
        print(f"{'Support connected components':58}: {component_count}")
        print(f"{'Largest component cells / share':58}: {largest_component} / {largest_fraction:.12f}")
        print(f"{'Unsupported-cell policy needed':58}: YES")
        print(f"{'Unsupported-cell fill performed':58}: NO")
        print(f"{'Full-grid plume authorized':58}: NO")
        print(f"{'Map-back re-executed':58}: NO")
        print(f"{'Internal test / OOD reopened':58}: NO / NO")
        for name in files:
            print(f"{name} SHA: {sha(out / name)}")
        print(f"V16E14_Support_By_Layer.csv SHA: {sha(layer_path)}")
        print("Output:", out)
        print("NEXT:", NEXT_PASS)
        return 0

    except Exception as exc:
        print(f"\n[FAIL] V16E-14 did not close: {exc}")
        try:
            bdir = compute / BLOCKED_REL
            bdir.mkdir(parents=True, exist_ok=True)
            report = {
                "milestone": MILESTONE,
                "status": BLOCKED,
                "exception": repr(exc),
                "gates": g.items,
                "E13R1_modified": False,
                "mapback_reexecuted": False,
                "unsupported_cell_fill_performed": False,
                "full_grid_plume_authorized": False,
                "next_milestone": NEXT_FAIL,
            }
            p = bdir / "V16E14_Blocked_Independent_MapBack_Audit.json"
            atomic_write(p, enc(report))
            print("Blocked report SHA:", sha(p))
            print("Blocked output:", bdir)
        except Exception:
            pass
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
