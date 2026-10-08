#!/usr/bin/env python3
"""PAD-Stream V16E-13-R1
Native-Dtype Identity Repair and Controlled Conservative Streamline-to-Grid Map-Back Execution.

Revision of blocked V16E-13, authorized by V16E-12-R1.

Repair scope: array identity is checked in the exact persisted/native dtype before
any numerical working-copy conversion. The parent E13 cast saturation_100d to
float64 before comparing its E12-R1 frozen array hash, causing a representation-
only identity failure before map-back execution.

This milestone executes exactly one supported-cell map-back of the immutable
V16E-11-R2 mixed streamline state using the frozen Version-15 SG7D1 operator
semantics. Unsupported cells remain NaN. No fill, full-grid projection, plume
thresholding, training, inference, or upstream physics recomputation occurs.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
from typing import Any

import numpy as np

MILESTONE = "V16E-13-R1"
SUCCESS = "V16E13_R1_NATIVE_DTYPE_IDENTITY_REPAIRED_CONSERVATIVE_MAPBACK_PASS"
BLOCKED = "V16E13_R1_NATIVE_DTYPE_IDENTITY_REPAIR_CONSERVATIVE_MAPBACK_BLOCKED"
NEXT_PASS = "V16E-14 — Independent SGSim 100-Day Map-Back Conservation / Support Audit"
NEXT_FAIL = "V16E-13-R2 — Repair only the failed E13-R1 gate; preserve E11-R2, E12-R1, and blocked E13 evidence"

PARENT_E13_RUNNER = (
    "PAD_Stream_V16E13_SGSim_100Day_Controlled_Conservative_Streamline_to_Grid_MapBack_Execution.py",
    "da889a51d70832b1d4e7b67e7a470a7d96759bd94db1bccd31ba8b4f78a7a5e3",
)
PARENT_E13_BLOCKED_REL = Path("provenance/hybrid_dp/V16E13_BLOCKED_CONSERVATIVE_MAPBACK")
PARENT_E13_BLOCKED_AUDIT = "V16E13_Blocked_Conservative_MapBack_Audit.json"

E12R1_RUNNER = (
    "PAD_Stream_V16E12_R1_Route_Semantics_Reconciliation_and_Conservative_MapBack_Protocol_Freeze.py",
    "fdd4c3ad5488fbe90d9d35764608363265b6c0831835e517ea3bdc4aec716971",
)
E12R1_REL = Path("provenance/hybrid_dp/V16E12_R1_ROUTE_SEMANTICS_RECONCILED_PILOT_EVIDENCE_AND_MAPBACK_PROTOCOL_FREEZE")
E12R1 = {
    "evidence": ("V16E12_R1_SGSim_100Day_Streamline_Pilot_Evidence_Freeze.json", "825be2644a343bacf2b89a20a6508914504a22689fe8aaf8b1309fb990b0d1c0"),
    "protocol": ("V16E12_R1_Conservative_MapBack_Protocol.json", "71da16ef29f643858539505dc3a139b86b20ba92ebde3f82ecb810845a85bb69"),
    "results": ("V16E12_R1_Protocol_Freeze_Results.json", "d544d00c8ac0c52bda9476ec33f68c769e92972e3cd636fa1fc15349a96f8156"),
    "summary": ("PAD_Stream_V16E12_R1_Summary.json", "987331326babe641c2c06243a00cc95c74812a7cba558ee6e08d43f17b9d4f4a"),
    "handoff": ("V16E12_R1_Handoff.md", "42dd809bc9e0db4256efdbe9700b3b712c02d033b587ea3a8735d427d18d12a3"),
}

E11R2_REL = Path("pilots/hybrid_dp/V16E11_R2_SGSIM_100D_CONTROLLED_STREAMLINE_PILOT")
E11R2_PILOT = (
    "V16E11_R2_SGSim_100Day_Streamline_Pilot.npz",
    "710720e933d740787868a9894fa04f90e88429c120d9f86a52b750f4c41db844",
)

MAPBACK_SOURCE = "PAD_Stream_V15SG7D1_Conservative_Frozen_L2_Streamline_to_Grid_MapBack.py"
OUT_REL = Path("pilots/hybrid_dp/V16E13_R1_SGSIM_100D_CONTROLLED_CONSERVATIVE_MAPBACK")

EXPECTED_NSTREAM = 1078
EXPECTED_NXI = 201
EXPECTED_GRID = (15, 50, 50)
EXPECTED_ROUTE_COUNTS = {10:462, 12:0, 20:41, 30:575, 99:0}

PROHIBITIONS = [
    "NO CHANGE TO BLOCKED V16E-13 PARENT EVIDENCE.",
    "NO CHANGE TO E12-R1 FROZEN ARRAY HASHES; HASH THE PERSISTED NATIVE DTYPE FIRST.",
    "NO TRAINING OR GRADIENT UPDATE.",
    "NO CHECKPOINT LOAD OR MODEL INFERENCE.",
    "NO PRESSURE / DARCY / POLLOCK / TOF RECOMPUTATION.",
    "NO CHANGE TO E11-R2 STREAMLINE SATURATION, ROUTES, OR FALLBACKS.",
    "NO ROUTE-SPECIFIC GRID OPERATOR.",
    "NO NODE-ONLY OR NEAREST-CELL DEPOSITION SUBSTITUTE.",
    "NO UNSUPPORTED-CELL FILL, INTERPOLATION, OR BACKGROUND COMPLETION.",
    "NO GLOBAL FULL-GRID CONSERVATIVE PROJECTION.",
    "NO SG7E THRESHOLDING OR FULL-GRID PLUME CLAIM.",
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
    if isinstance(v, dict): return {str(k): native(x) for k,x in v.items()}
    if isinstance(v, (list,tuple)): return [native(x) for x in v]
    if isinstance(v, np.ndarray): return native(v.tolist())
    if isinstance(v, np.generic): return v.item()
    if isinstance(v, Path): return str(v)
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
    spec = importlib.util.spec_from_file_location("v15_sg7d1_authority", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not construct V15-SG7D1 import specification")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def mapback_once(authority, xyz: np.ndarray, sat: np.ndarray, weights: np.ndarray):
    coord = authority.infer_coordinate_units_and_origin(xyz)
    xyz_m = np.asarray(coord["xyz_local_m"], dtype=np.float64)

    grid_shape = tuple(authority.GRID_SHAPE)
    denominator = np.zeros(grid_shape, dtype=np.float64)
    numerator = np.zeros(grid_shape, dtype=np.float64)
    segment_piece_count = np.zeros(grid_shape, dtype=np.int64)
    streamline_visit_count = np.zeros(grid_shape, dtype=np.int64)
    last_seen = np.full(grid_shape, -1, dtype=np.int64)

    lo = np.asarray([0.0,0.0,0.0], dtype=np.float64)
    hi = np.asarray([authority.LX_M, authority.LY_M, authority.LZ_M], dtype=np.float64)

    total_input_weighted_length = 0.0
    total_deposited_weighted_length = 0.0
    total_input_weighted_sat_length = 0.0
    total_deposited_weighted_sat_length = 0.0
    total_segments = 0
    clipped_segments = 0
    skipped_zero_segments = 0
    total_pieces = 0

    nstream, nxi = sat.shape
    for m in range(nstream):
        wm = float(weights[m])
        for j in range(nxi - 1):
            p0 = xyz_m[m,j]
            p1 = xyz_m[m,j+1]
            if not (np.all(np.isfinite(p0)) and np.all(np.isfinite(p1))):
                continue
            segvec = p1 - p0
            seglen = float(np.linalg.norm(segvec))
            if seglen <= 0.0:
                skipped_zero_segments += 1
                continue
            total_segments += 1
            s0 = float(sat[m,j]); s1 = float(sat[m,j+1])
            source_sat_avg = 0.5 * (s0+s1)
            total_input_weighted_length += wm * seglen
            total_input_weighted_sat_length += wm * source_sat_avg * seglen

            clipped = authority.clip_segment_to_box(p0,p1,lo,hi)
            if clipped is None:
                continue
            q0,q1,t0_orig,t1_orig = clipped
            clipped_len = float(np.linalg.norm(q1-q0))
            if clipped_len <= 0.0:
                continue
            if t0_orig > 0.0 or t1_orig < 1.0:
                clipped_segments += 1

            pieces = authority.split_segment_by_cell_boundaries(q0,q1)
            for u_mid, dl, k, jj, i in pieces:
                t_mid = t0_orig + u_mid * (t1_orig - t0_orig)
                smid = s0 + t_mid * (s1-s0)
                measure = wm * dl
                denominator[k,jj,i] += measure
                numerator[k,jj,i] += measure * smid
                segment_piece_count[k,jj,i] += 1
                if last_seen[k,jj,i] != m:
                    streamline_visit_count[k,jj,i] += 1
                    last_seen[k,jj,i] = m
                total_deposited_weighted_length += measure
                total_deposited_weighted_sat_length += measure * smid
                total_pieces += 1

    supported = denominator > 0.0
    s_grid = np.full(grid_shape, np.nan, dtype=np.float64)
    s_grid[supported] = numerator[supported] / denominator[supported]

    support_abs = abs(total_deposited_weighted_length-total_input_weighted_length)
    support_rel = support_abs/max(abs(total_input_weighted_length),1e-30)
    sat_abs = abs(total_deposited_weighted_sat_length-total_input_weighted_sat_length)
    sat_rel = sat_abs/max(abs(total_input_weighted_sat_length),1e-30)

    return {
        "saturation_grid": s_grid,
        "support_denominator": denominator,
        "support_numerator": numerator,
        "supported_mask": supported,
        "segment_piece_count": segment_piece_count,
        "streamline_visit_count": streamline_visit_count,
        "coordinate": coord,
        "total_input_weighted_length": total_input_weighted_length,
        "total_deposited_weighted_length": total_deposited_weighted_length,
        "total_input_weighted_sat_length": total_input_weighted_sat_length,
        "total_deposited_weighted_sat_length": total_deposited_weighted_sat_length,
        "support_closure_abs": support_abs,
        "support_closure_rel": support_rel,
        "sat_measure_closure_abs": sat_abs,
        "sat_measure_closure_rel": sat_rel,
        "total_segments": total_segments,
        "clipped_segments": clipped_segments,
        "skipped_zero_segments": skipped_zero_segments,
        "total_pieces": total_pieces,
    }

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=str(Path(__file__).resolve().parent))
    ap.add_argument("--compute-root", default="/content/drive/MyDrive/PAD_Stream_Compute")
    args = ap.parse_args()
    repo = Path(args.repo_root).resolve()
    compute = Path(args.compute_root).resolve()
    out = compute / OUT_REL
    g = Gates()

    print("="*126)
    print("PAD-Stream V16E-13-R1 Native-Dtype Identity Repair and Controlled Conservative Streamline-to-Grid Map-Back Execution")
    print("="*126)
    for line in PROHIBITIONS: print(line)

    try:
        print("\nBLOCKED V16E-13 PARENT EVIDENCE")
        bind(g, "parent_E13_runner", repo/PARENT_E13_RUNNER[0], PARENT_E13_RUNNER[1])
        parent_blocked_path = compute/PARENT_E13_BLOCKED_REL/PARENT_E13_BLOCKED_AUDIT
        g.check("parent_E13_blocked_audit_exists", parent_blocked_path.is_file(), str(parent_blocked_path))
        parent_blocked_sha = sha(parent_blocked_path)
        parent_blocked = read_json(parent_blocked_path)
        g.check("parent_E13_status_BLOCKED", parent_blocked.get("status") == "V16E13_SGSIM_100D_CONTROLLED_CONSERVATIVE_MAPBACK_BLOCKED")
        g.check("parent_E13_failed_exactly_at_saturation_native_identity_gate", parent_blocked.get("exception") == "GateError('pilot_array_SHA_exact_saturation_100d')")
        failed_parent = [k for k,v in parent_blocked.get("gates",{}).items() if not bool(v.get("passed",False))]
        g.check("parent_E13_single_failed_gate", failed_parent == ["pilot_array_SHA_exact_saturation_100d"], str(failed_parent))
        g.check("parent_E13_mapback_not_accepted", parent_blocked.get("mapback_accepted") is False)
        g.check("parent_E13_unsupported_fill_not_performed", parent_blocked.get("unsupported_cell_fill_performed") is False)
        g.check("parent_E13_full_grid_not_authorized", parent_blocked.get("full_grid_plume_authorized") is False)
        g.check("parent_E13_all_preceding_identity_and_input_gates_passed", all(bool(v.get("passed",False)) for k,v in parent_blocked.get("gates",{}).items() if k != "pilot_array_SHA_exact_saturation_100d"))

        print("\nV16E-12-R1 AUTHORITY")
        bind(g, "E12R1_runner", repo/E12R1_RUNNER[0], E12R1_RUNNER[1])
        parent_paths = {}
        for key,(fn,hs) in E12R1.items():
            p = compute/E12R1_REL/fn
            bind(g, "E12R1_"+key, p, hs)
            parent_paths[key] = p
        protocol = read_json(parent_paths["protocol"])
        results = read_json(parent_paths["results"])
        summary = read_json(parent_paths["summary"])
        g.check("E12R1_status_PASS", summary.get("status") == "PASS")
        g.check("E12R1_E13_authorized", results.get("E13_authorized") is True)
        g.check("E12R1_mapback_not_already_performed", results.get("mapback_performed") is False)
        g.check("E12R1_unsupported_nan", protocol["operator_contract"]["unsupported_cell_state"] == "NaN")
        g.check("E12R1_no_fill_authority", protocol["operator_contract"]["unsupported_fill_authorized"] is False)
        g.check("E12R1_closure_targets_exact", float(protocol["operator_contract"]["support_closure_relative_max"]) == 1e-8 and float(protocol["operator_contract"]["saturation_measure_closure_relative_max"]) == 1e-8)

        print("\nV16E-11-R2 IMMUTABLE MAP-BACK INPUT — NATIVE-DTYPE IDENTITY REPAIR")
        pilot_path = compute/E11R2_REL/E11R2_PILOT[0]
        bind(g, "E11R2_pilot", pilot_path, E11R2_PILOT[1])
        with np.load(pilot_path, allow_pickle=False) as z:
            required = ["physical_time_days","xi","xyz_m","tau_s","tau_end_s","weights_m3_s","route_code","route_label","saturation_100d"]
            g.check("pilot_required_inputs_present", all(k in z.files for k in required), str(z.files))
            physical_time = float(np.asarray(z["physical_time_days"]).item())

            # Identity authority: hash exact persisted arrays BEFORE any dtype conversion.
            raw = {k: np.asarray(z[k]) for k in [
                "xi","xyz_m","tau_s","tau_end_s","weights_m3_s",
                "route_code","route_label","saturation_100d"
            ]}
            frozen_hashes = protocol["parent_evidence"]["pilot_array_sha256"]
            for k,a in raw.items():
                g.check("pilot_native_array_SHA_exact_"+k, arr_sha(a) == frozen_hashes[k])

            raw_sat = raw["saturation_100d"]
            parent_cast_hash = arr_sha(np.asarray(raw_sat, dtype=np.float64))
            g.check("parent_E13_failure_mechanism_reproduced",
                    arr_sha(raw_sat) == frozen_hashes["saturation_100d"]
                    and parent_cast_hash != frozen_hashes["saturation_100d"],
                    f"persisted_dtype={raw_sat.dtype}; native={arr_sha(raw_sat)}; premature_float64={parent_cast_hash}")

            # Working copies may be promoted only AFTER immutable identity closes.
            xi = np.asarray(raw["xi"])
            xyz = np.asarray(raw["xyz_m"], dtype=np.float64)
            tau = np.asarray(raw["tau_s"], dtype=np.float64)
            tau_end = np.asarray(raw["tau_end_s"], dtype=np.float64)
            weights = np.asarray(raw["weights_m3_s"], dtype=np.float64)
            route_code = np.asarray(raw["route_code"])
            route_label = np.asarray(raw["route_label"])
            sat = np.asarray(raw_sat, dtype=np.float64)

            g.check("pilot_100_days_exact", physical_time == 100.0)
            g.check("pilot_streamline_shape_exact", sat.shape == (EXPECTED_NSTREAM,EXPECTED_NXI))
            g.check("pilot_geometry_shape_exact", xyz.shape == (EXPECTED_NSTREAM,EXPECTED_NXI,3))
            g.check("pilot_tau_shape_exact", tau.shape == (EXPECTED_NSTREAM,EXPECTED_NXI) and tau_end.shape == (EXPECTED_NSTREAM,))
            g.check("pilot_weights_positive", weights.shape == (EXPECTED_NSTREAM,) and np.all(np.isfinite(weights)) and np.all(weights>0.0))
            g.check("pilot_finite_saturation", np.all(np.isfinite(sat)))
            g.check("pilot_route_counts_preserved", {code:int(np.sum(route_code==code)) for code in EXPECTED_ROUTE_COUNTS} == EXPECTED_ROUTE_COUNTS)
            g.check("working_float64_conversion_after_identity_only", sat.dtype == np.float64 and xyz.dtype == np.float64 and weights.dtype == np.float64)

        print("\nVERSION-15 SG7D1 EXECUTION AUTHORITY")
        source_path = repo/MAPBACK_SOURCE
        g.check("V15SG7D1_source_exists", source_path.is_file(), str(source_path))
        recorded = protocol["frozen_mapback_source_lineage"][MAPBACK_SOURCE]["sha256"]
        g.check("V15SG7D1_source_SHA_matches_E12R1", sha(source_path) == recorded, sha(source_path))
        authority = load_source_module(source_path)
        g.check("V15SG7D1_grid_shape_exact", tuple(authority.GRID_SHAPE) == EXPECTED_GRID)
        g.check("V15SG7D1_required_functions_present", all(hasattr(authority,n) for n in ["infer_coordinate_units_and_origin","clip_segment_to_box","split_segment_by_cell_boundaries"]))

        print("\nCONTROLLED CONSERVATIVE MAP-BACK EXECUTION")
        first = mapback_once(authority,xyz,sat,weights)
        second = mapback_once(authority,xyz,sat,weights)

        sgrid = first["saturation_grid"]
        denom = first["support_denominator"]
        numer = first["support_numerator"]
        supported = first["supported_mask"]
        supported_cells = int(np.sum(supported))
        unsupported_cells = int(supported.size-supported_cells)
        support_fraction = float(np.mean(supported))

        g.check("deterministic_repeat_saturation_exact", np.array_equal(first["saturation_grid"],second["saturation_grid"],equal_nan=True))
        g.check("deterministic_repeat_denominator_exact", np.array_equal(denom,second["support_denominator"]))
        g.check("deterministic_repeat_numerator_exact", np.array_equal(numer,second["support_numerator"]))
        g.check("deterministic_repeat_support_mask_exact", np.array_equal(supported,second["supported_mask"]))
        g.check("at_least_one_supported_cell", supported_cells > 0)
        g.check("unsupported_cells_explicit_nan", np.all(np.isnan(sgrid[~supported])))
        g.check("supported_cells_finite", np.all(np.isfinite(sgrid[supported])))
        g.check("mapped_bounds_within_streamline_state", float(np.nanmin(sgrid)) >= float(np.min(sat))-1e-10 and float(np.nanmax(sgrid)) <= float(np.max(sat))+1e-10)
        g.check("support_closure_le_1e8", first["support_closure_rel"] <= 1e-8, f"{first['support_closure_rel']:.12e}")
        g.check("sat_measure_closure_le_1e8", first["sat_measure_closure_rel"] <= 1e-8, f"{first['sat_measure_closure_rel']:.12e}")
        g.check("no_full_grid_fill", unsupported_cells == int(np.sum(~supported)))

        array_hashes = {
            "saturation_grid_float64":arr_sha(sgrid),
            "support_denominator":arr_sha(denom),
            "support_numerator":arr_sha(numer),
            "supported_mask":arr_sha(supported.astype(np.uint8)),
            "segment_piece_count":arr_sha(first["segment_piece_count"]),
            "streamline_visit_count":arr_sha(first["streamline_visit_count"]),
        }

        out.mkdir(parents=True, exist_ok=True)
        numerical_path = out/"V16E13_R1_SGSim_100Day_Conservative_MapBack.npz"
        np.savez_compressed(
            numerical_path,
            saturation_grid=sgrid.astype(np.float32),
            saturation_grid_float64=sgrid.astype(np.float64),
            support_denominator=denom.astype(np.float64),
            support_numerator=numer.astype(np.float64),
            supported_mask=supported.astype(np.uint8),
            segment_piece_count=first["segment_piece_count"].astype(np.int64),
            streamline_visit_count=first["streamline_visit_count"].astype(np.int64),
            grid_shape=np.asarray(authority.GRID_SHAPE,dtype=np.int64),
            cell_size_m=np.asarray([authority.DX_M,authority.DY_M,authority.DZ_M],dtype=np.float64),
            domain_size_m=np.asarray([authority.LX_M,authority.LY_M,authority.LZ_M],dtype=np.float64),
            coordinate_scale_to_m=np.asarray(first["coordinate"]["scale_to_m"],dtype=np.float64),
            coordinate_origin_shift_m=np.asarray(first["coordinate"]["origin_shift_m"],dtype=np.float64),
            physical_time_days=np.asarray(100.0,dtype=np.float64),
            source_pilot_sha256=np.asarray(E11R2_PILOT[1]),
            source_protocol_sha256=np.asarray(E12R1["protocol"][1]),
            total_input_weighted_length=np.asarray(first["total_input_weighted_length"],dtype=np.float64),
            total_deposited_weighted_length=np.asarray(first["total_deposited_weighted_length"],dtype=np.float64),
            total_input_weighted_sat_length=np.asarray(first["total_input_weighted_sat_length"],dtype=np.float64),
            total_deposited_weighted_sat_length=np.asarray(first["total_deposited_weighted_sat_length"],dtype=np.float64),
        )

        audit = {
            "milestone":MILESTONE,
            "status":"PASS",
            "authority":{
                "parent_E13_runner_sha256":PARENT_E13_RUNNER[1],
                "parent_E13_blocked_audit_sha256":parent_blocked_sha,
                "identity_repair":"hash exact persisted/native arrays before any working dtype conversion",
                "persisted_saturation_dtype":str(raw_sat.dtype),
                "E12R1_runner_sha256":E12R1_RUNNER[1],
                "E12R1_protocol_sha256":E12R1["protocol"][1],
                "E11R2_pilot_sha256":E11R2_PILOT[1],
                "V15SG7D1_source_sha256":recorded,
            },
            "input":{
                "physical_time_days":physical_time,
                "streamlines":EXPECTED_NSTREAM,
                "nodes":EXPECTED_NXI,
                "route_counts":{"HYBRID10":462,"HYBRID12":0,"EXACT_R2":41,"SG7A":575},
                "route_labels_are_provenance_only":True,
            },
            "operator":{
                "method":"V15-SG7D1 flow-weighted piecewise-linear segment/cell intersection accumulation",
                "deposition_measure":"streamline_weight * subsegment_length_m",
                "unsupported_cell_policy":"NaN / no fill",
                "coordinate_input_units":first["coordinate"]["input_units"],
                "coordinate_scale_to_m":first["coordinate"]["scale_to_m"],
                "coordinate_origin_shift_m":first["coordinate"]["origin_shift_m"],
            },
            "mapback":{
                "grid_shape":list(EXPECTED_GRID),
                "supported_cells":supported_cells,
                "unsupported_cells":unsupported_cells,
                "support_fraction":support_fraction,
                "total_segments":first["total_segments"],
                "clipped_segments":first["clipped_segments"],
                "zero_length_segments_skipped":first["skipped_zero_segments"],
                "deposition_pieces":first["total_pieces"],
                "support_closure_abs":first["support_closure_abs"],
                "support_closure_rel":first["support_closure_rel"],
                "sat_measure_closure_abs":first["sat_measure_closure_abs"],
                "sat_measure_closure_rel":first["sat_measure_closure_rel"],
                "streamline_saturation_min":float(np.min(sat)),
                "streamline_saturation_max":float(np.max(sat)),
                "mapped_saturation_min":float(np.nanmin(sgrid)),
                "mapped_saturation_max":float(np.nanmax(sgrid)),
                "deterministic_repeat_exact":True,
                "array_sha256":array_hashes,
            },
            "firewall":{
                "training":False,"model_inference":False,"pressure_Darcy_Pollock_TOF_recomputed":False,
                "transport_state_changed":False,"unsupported_cells_filled":False,"full_grid_projection":False,
                "SG7E_thresholding":False,"internal_test_reopened":False,"OOD_reopened":False,
            },
            "independent_post_mapback_audit_complete":False,
            "full_grid_plume_authorized":False,
            "next_milestone":NEXT_PASS,
            "gates":g.items,
        }
        contract = {
            "milestone":MILESTONE,
            "status":"PASS",
            "parent_blocked_E13_audit_sha256":parent_blocked_sha,
            "native_dtype_identity_repair_closed":True,
            "numerical_artifact":numerical_path.name,
            "numerical_artifact_sha256":sha(numerical_path),
            "array_sha256":array_hashes,
            "supported_cell_field_is_candidate":True,
            "unsupported_cells_remain_nan":True,
            "unsupported_cell_fill_authorized":False,
            "independent_V16_audit_required":True,
            "full_grid_plume_authorized":False,
            "next_milestone":NEXT_PASS,
        }
        summary_out = {
            "milestone":MILESTONE,"status":"PASS","physical_time_days":100.0,
            "parent_blocked_E13_audit_sha256":parent_blocked_sha,"native_dtype_identity_repair_closed":True,
            "grid_shape":list(EXPECTED_GRID),"supported_cells":supported_cells,"unsupported_cells":unsupported_cells,
            "support_fraction":support_fraction,"support_closure_rel":first["support_closure_rel"],
            "sat_measure_closure_rel":first["sat_measure_closure_rel"],"mapped_saturation_min":float(np.nanmin(sgrid)),
            "mapped_saturation_max":float(np.nanmax(sgrid)),"deterministic_repeat_exact":True,
            "unsupported_cells_filled":False,"full_grid_plume_authorized":False,
            "internal_test_reopened":False,"OOD_reopened":False,"next_milestone":NEXT_PASS,
        }
        handoff = f"""# PAD-Stream V16E-13-R1 — Native-Dtype Identity-Repaired Controlled Conservative Map-Back PASS\n\nThe immutable V16E-11-R2 100-day mixed streamline state was mapped onto the 15x50x50 SGSim grid using the source-bound V15-SG7D1 flow-weighted piecewise-linear segment/cell intersection operator frozen by V16E-12-R1. Unsupported cells remain NaN and no full-grid completion or plume thresholding was performed.\n\nSupported cells: {supported_cells}\nUnsupported cells: {unsupported_cells}\nSupport fraction: {support_fraction:.12f}\nSupport closure rel: {first['support_closure_rel']:.12e}\nSaturation-measure closure rel: {first['sat_measure_closure_rel']:.12e}\n\nThe mapped supported-cell field is a candidate only until an independent V16 conservation/support audit closes.\n\nNEXT: {NEXT_PASS}\n""".encode("utf-8")

        files = {
            "V16E13_R1_Conservative_MapBack_Audit.json":enc(audit),
            "V16E13_R1_Conservative_MapBack_Contract.json":enc(contract),
            "PAD_Stream_V16E13_R1_Summary.json":enc(summary_out),
            "V16E13_R1_Handoff.md":handoff,
        }
        for name,data in files.items():
            p=out/name; tmp=p.with_suffix(p.suffix+".tmp"); tmp.write_bytes(data); os.replace(tmp,p)

        print("\n"+"="*126)
        print("V16E-13-R1 RESULT: PASS")
        print("="*126)
        print(f"{'SGSim grid':58}: 15 x 50 x 50")
        print(f"{'Supported / unsupported cells':58}: {supported_cells} / {unsupported_cells}")
        print(f"{'Support fraction':58}: {support_fraction:.9f}")
        print(f"{'Support closure relative':58}: {first['support_closure_rel']:.12e}")
        print(f"{'Saturation-measure closure relative':58}: {first['sat_measure_closure_rel']:.12e}")
        print(f"{'Mapped saturation min / max':58}: {np.nanmin(sgrid):.12g} / {np.nanmax(sgrid):.12g}")
        print(f"{'Deterministic repeat exact':58}: YES")
        print(f"{'Unsupported-cell fill performed':58}: NO")
        print(f"{'Full-grid plume authorized':58}: NO")
        print(f"{'Internal test / OOD reopened':58}: NO / NO")
        print("V16E13_R1_SGSim_100Day_Conservative_MapBack.npz SHA:", sha(numerical_path))
        for name in files: print(f"{name} SHA: {sha(out/name)}")
        print("Output:",out)
        print("NEXT:",NEXT_PASS)
        return 0
    except Exception as exc:
        print(f"\n[FAIL] V16E-13-R1 did not close: {exc}")
        try:
            bdir=compute/"provenance/hybrid_dp/V16E13_R1_BLOCKED_CONSERVATIVE_MAPBACK"
            bdir.mkdir(parents=True,exist_ok=True)
            report={"milestone":MILESTONE,"status":BLOCKED,"exception":repr(exc),"gates":g.items,
                    "mapback_accepted":False,"unsupported_cell_fill_performed":False,"full_grid_plume_authorized":False,
                    "next_milestone":NEXT_FAIL}
            p=bdir/"V16E13_R1_Blocked_Conservative_MapBack_Audit.json"; p.write_bytes(enc(report))
            print("Blocked report SHA:",sha(p)); print("Blocked output:",bdir)
        except Exception: pass
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
