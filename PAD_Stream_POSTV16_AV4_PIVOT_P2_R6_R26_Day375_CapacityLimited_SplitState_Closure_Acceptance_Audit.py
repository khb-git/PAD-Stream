#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, hashlib, importlib.util, io, json, subprocess, sys
from pathlib import Path
from typing import Any
import numpy as np

M = "POSTV16-AV4-PIVOT-P2-R6-R26"
NAME = "Day375 Capacity-Limited Split-State Restart Representation Closure and Acceptance Audit"
PASS = "AV4PIVOTP2R6R26_DAY375_CAPACITY_LIMITED_SPLIT_STATE_RESTART_REPRESENTATION_CLOSURE_ACCEPTANCE_AUDIT_PASS_EXACT_R25R3_STATE_ACCEPTED_NO_STATE_REWRITE"
BLOCK = "AV4PIVOTP2R6R26_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "890563b02ec99dcf78e8df093ccc604e9394423b"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

GRID = (15, 50, 50)
NCELL = 37500
NSL, NN, NCV = 1078, 201, 200
NCVT = NSL * NCV
DAY = 375.0
DAY_TO_S = 86400.0
MASS_TOL, LEDGER_TOL, CAPACITY_TOL = 1e-6, 1e-6, 1e-7
OPT_REL_TOL, SAT_TOL = 1e-10, 1e-10

R25R3_REL = BASE / "POSTV16_AV4_PIVOT_P2_R6_R25_R3_Controlled_Day375_CapacityLimited_ExactSupport_SplitState_Reprojection_Execution_Stage2_PresolveOff"
R25R3_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R25_R3_Summary.json"
R25R3_EXECUTION = "POSTV16_AV4_PIVOT_P2_R6_R25_R3_Execution_Contract.json"
R25R3_DECISION = "POSTV16_AV4_PIVOT_P2_R6_R25_R3_Decision_Contract.json"
R25R3_STATE = "POSTV16_AV4_PIVOT_P2_R6_R25_R3_CapacityLimited_SplitState_Day375.npz"
R25R3_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R25_R3_Artifact_Manifest.csv"
R25R3_STATUS = "AV4PIVOTP2R6R25R3_DAY375_CAPACITY_LIMITED_EXACT_SUPPORT_SPLIT_STATE_REPROJECTION_EXECUTION_STAGE2_PRESOLVE_OFF_PASS_NO_MAPBACK_NO_TIME_ADVANCE"
R25R3_CLASSIFICATION = "R6R25R3_CAPACITY_LIMITED_EXACT_SUPPORT_SPLIT_STATE_REPROJECTION_EXECUTION_EXACT_FRONTIER_STAGE2_PRESOLVE_OFF_PASS_R26_ACCEPTANCE_AUDIT_NEXT"
R25R3_STATE_SHA256 = "9893e2476bce1d46213cdd1304e60ad93b49ea285e084d06743a2ffab25f721f"

R25_FAIL_REL = BASE / "POSTV16_AV4_PIVOT_P2_R6_R25_SCIENTIFIC_FAIL"
R25_FAIL = "POSTV16_AV4_PIVOT_P2_R6_R25_Scientific_Fail_Report.json"
R25_FAIL_SHA256 = "0a6b434db97e8a7f8052fb4eea53071a6fce6b8d325740a0562df6ff44a99678"

R25R2_REL = BASE / "POSTV16_AV4_PIVOT_P2_R6_R25_R2_ExactFrontier_HiGHS_PresolveOff_SolverConditioning_Repair_Design_Freeze"
R25R2_PROTOCOL = "POSTV16_AV4_PIVOT_P2_R6_R25_R2_ExactFrontier_SolverConditioning_Repair_Protocol.json"
R25R2_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R25_R2_Artifact_Manifest.csv"

R24_REL = BASE / "POSTV16_AV4_PIVOT_P2_R6_R24_Day375_R22_Geometry_Reprojection_Capacity_Representation_Design_Freeze"
R24_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R24_Summary.json"
R24_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R24_Artifact_Manifest.csv"
R24_MAX_REPRESENTABLE_S0_MASS_KG = 52457458.82473308
R24_MINIMUM_UNAVOIDABLE_S0_RESIDUAL_KG = 6646660.64504873
R24_MINIMUM_UNAVOIDABLE_S0_RESIDUAL_FRACTION = 0.1124568085046419
R24_S0_MASS_KG = 59104119.46978181

R22_REL = BASE / "POSTV16_AV4_PIVOT_P2_R6_R22_Controlled_Day375_AcceptedState_Darcy_Pollock_TOF_Regeneration"
R22_EPOCH = "POSTV16_AV4_PIVOT_P2_R6_R22_Day375_Regenerated_Darcy_Pollock_TOF_Epoch.npz"
R22_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R22_Artifact_Manifest.csv"
R22_EPOCH_SHA256 = "7f030fd3676eb3b61bc7f341dff8cb82659e87e210640a9488bf6fb15e7bd80e"

CLOSURE_TOKEN = "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_R1_R1_R1_R1"
CLOSURE_REL = BASE / (CLOSURE_TOKEN + "_Comprehensive_Technical_Closure_and_Pressure_Refresh_Acceptance")
PRESSURE_EPOCH = CLOSURE_TOKEN + "_Accepted_Day375_Pressure_Epoch.npz"
CLOSURE_MANIFEST = CLOSURE_TOKEN + "_Artifact_Manifest.csv"
PRESSURE_EPOCH_SHA256 = "99d73cab1d33191a68578f29d3c03f9fac07ed77c39e124cc8eb5e5bf75aa84d"
R20_ACCEPTED_STATE_SHA256 = "e209adb5a169008698db9acb24e5cade82df3f6991b5174515d5957901bceb67"

R25R3_RUNNER = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R25_R3_Controlled_CapacityLimited_Reprojection_Stage2_PresolveOff.py"
R25R3_BLOB = "65cab626419137b191f2c53a4c543d9805ccf68d"
R25R2_RUNNER = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R25_R2_ExactFrontier_HiGHS_PresolveOff_Design_Freeze.py"
R25R2_BLOB = "baa5be79dbc90bad9c523cd6f682e285187c24b8"
R24_RUNNER = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R24_Day375_R22_Geometry_Reprojection_Capacity_Representation_Design_Freeze.py"
R24_BLOB = "9168baf3155e712b9c342239bed9ab4b1d787691"
SG7D = "PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"
SG7D_BLOB = "890088c0c0fcab415a2c7351c5079ca8ee12bf82"
E37A = "PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB = "0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"
R2 = "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"
SOURCE_BLOBS = {
    R25R3_RUNNER: R25R3_BLOB, R25R2_RUNNER: R25R2_BLOB, R24_RUNNER: R24_BLOB,
    SG7D: SG7D_BLOB, E37A: E37A_BLOB, R2: R2_BLOB,
}

OUT_TOKEN = "POSTV16_AV4_PIVOT_P2_R6_R26"
OUT_REL = BASE / (OUT_TOKEN + "_Day375_CapacityLimited_SplitState_Restart_Representation_Closure_and_Acceptance_Audit")
BLOCK_REL = BASE / (OUT_TOKEN + "_BLOCKED")

class GateError(RuntimeError): pass

def gt(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()

def sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""): h.update(chunk)
    return h.hexdigest()

def js(path: Path): return json.loads(path.read_text(encoding="utf-8"))

def csvr(path: Path):
    with open(path, newline="", encoding="utf-8") as f: return list(csv.DictReader(f))

def csvb(rows):
    if not rows: return b""
    fields = []
    for row in rows:
        for k in row:
            if k not in fields: fields.append(k)
    s = io.StringIO(newline="")
    w = csv.DictWriter(s, fieldnames=fields, lineterminator="\n")
    w.writeheader(); w.writerows(rows)
    return s.getvalue().encode()

def jb(obj): return (json.dumps(obj, indent=2, sort_keys=True) + "\n").encode()

def manifest(directory: Path, filename: str):
    out = {}
    for row in csvr(directory / filename):
        p = directory / row["file"]
        if not p.is_file(): raise GateError(f"manifest_missing:{p.name}")
        if sha(p) != row["sha256"]: raise GateError(f"manifest_sha:{p.name}")
        if p.stat().st_size != int(row["bytes"]): raise GateError(f"manifest_bytes:{p.name}")
        out[p.name] = row["sha256"]
    return out

def mod(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None: raise GateError(f"cannot_load:{path}")
    m = importlib.util.module_from_spec(spec); sys.modules[name] = m; spec.loader.exec_module(m)
    return m

def rebuild_support_target(grid_mass, op):
    gm = np.asarray(grid_mass, float).reshape(-1)
    stream = np.asarray(op["streamline"], np.int64).reshape(-1)
    node = np.asarray(op["node"], np.int64).reshape(-1)
    cell = np.asarray(op["flat_cell"], np.int64).reshape(-1)
    pv = np.asarray(op["pv_m3"], float).reshape(-1)
    cv = stream * NCV + node
    den = np.bincount(cell, weights=pv, minlength=NCELL)
    if np.any(den[cell] <= 0): raise GateError("zero_cell_denominator")
    sub = gm[cell] * pv / den[cell]
    key = cv * NCELL + cell
    uniq, inv = np.unique(key, return_inverse=True)
    return ((uniq // NCELL).astype(np.int64), (uniq % NCELL).astype(np.int64),
            np.bincount(inv, weights=sub, minlength=len(uniq)).astype(float))

def selftest():
    assert NCVT == NSL * NCV
    assert OUT_REL.name.startswith(OUT_TOKEN + "_")
    assert R25R3_STATE_SHA256 != R20_ACCEPTED_STATE_SHA256
    print("POSTV16 AV4 PIVOT P2-R6-R26 structural self-test: PASS")

def main(project_root: Path, drive_root: Path) -> int:
    root, drive = project_root.resolve(), drive_root.resolve()
    out, block_dir = drive / OUT_REL, drive / BLOCK_REL
    stage = "preflight"; gates = []

    def gate(name, cond, detail=None):
        ok = bool(cond)
        gates.append({"stage": stage, "gate": name, "pass": ok, "detail": "" if detail is None else repr(detail)})
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + ("" if detail is None else f" -- {detail}"))
        if not ok: raise GateError(name)

    try:
        stage = "preexisting_state_firewall"
        gate("no_preexisting_R26_PASS", not (out / f"PAD_Stream_{OUT_TOKEN}_Summary.json").exists())
        gate("no_preexisting_R26_BLOCK", not (block_dir / f"{OUT_TOKEN}_Blocked_Report.json").exists())

        stage = "repository_authority"
        gate("branch_exact", gt(root, "branch", "--show-current") == BRANCH)
        gate("parent_is_R25R3_commit", gt(root, "rev-parse", "HEAD^") == PARENT)
        gate("repository_clean", gt(root, "status", "--porcelain") == "")
        for filename, expected in SOURCE_BLOBS.items():
            p = root / filename
            gate(f"{Path(filename).stem}_present", p.is_file(), str(p))
            actual = gt(root, "hash-object", str(p)) if p.is_file() else "missing"
            gate(f"{Path(filename).stem}_blob_exact", actual == expected, actual)

        stage = "R25R3_authority"
        r25 = drive / R25R3_REL
        m25 = manifest(r25, R25R3_MANIFEST)
        s25, e25, d25 = js(r25 / R25R3_SUMMARY), js(r25 / R25R3_EXECUTION), js(r25 / R25R3_DECISION)
        state_path = r25 / R25R3_STATE
        gate("R25R3_status_exact", s25.get("status") == R25R3_STATUS, s25.get("status"))
        gate("R25R3_classification_exact", s25.get("classification") == R25R3_CLASSIFICATION, s25.get("classification"))
        gate("R25R3_manifest_state_SHA_exact", m25.get(R25R3_STATE) == R25R3_STATE_SHA256)
        gate("R25R3_state_file_SHA_exact", sha(state_path) == R25R3_STATE_SHA256, sha(state_path))
        gate("R25R3_summary_state_SHA_exact", s25.get("capacity_limited_split_state_sha256") == R25R3_STATE_SHA256)
        gate("R25R3_execution_state_SHA_exact", e25.get("capacity_limited_split_state_sha256") == R25R3_STATE_SHA256)
        gate("R26_authorized", d25.get("P2_R6_R26_authorized") is True)
        gate("R26_diagnostic_only", d25.get("P2_R6_R26_design_or_diagnostic_only") is True)
        gate("R26_state_SHA_bound", d25.get("P2_R6_R26_R25R3_state_sha256") == R25R3_STATE_SHA256)
        gate("transport_locked", d25.get("transport_execution_authorized") is False)
        gate("mapback_locked", d25.get("mapback_execution_authorized") is False)
        gate("time_locked", d25.get("physical_time_advance_authorized") is False)

        fail_path = drive / R25_FAIL_REL / R25_FAIL
        gate("R25_FAIL_SHA_preserved", fail_path.is_file() and sha(fail_path) == R25_FAIL_SHA256)
        r25r2 = drive / R25R2_REL; manifest(r25r2, R25R2_MANIFEST); p25r2 = js(r25r2 / R25R2_PROTOCOL)
        gate("R25R2_stage2_presolve_off", p25r2["solver_conditioning_repair"]["stage2"]["presolve"] is False)
        gate("R25R2_mass_floor_forbidden", p25r2["solver_conditioning_repair"]["mass_floor_relaxation_authorized"] is False)

        r24 = drive / R24_REL; manifest(r24, R24_MANIFEST); s24 = js(r24 / R24_SUMMARY)
        gate("R24_max_mass_exact", abs(float(s24["maximum_representable_S0_mass_kg"]) - R24_MAX_REPRESENTABLE_S0_MASS_KG) <= 1e-9)
        gate("R24_S0_residual_exact", abs(float(s24["minimum_unavoidable_S0_residual_kg"]) - R24_MINIMUM_UNAVOIDABLE_S0_RESIDUAL_KG) <= 1e-9)

        stage = "source_state_authority"
        r22 = drive / R22_REL; m22 = manifest(r22, R22_MANIFEST); r22p = r22 / R22_EPOCH
        gate("R22_epoch_SHA_exact", m22.get(R22_EPOCH) == R22_EPOCH_SHA256 and sha(r22p) == R22_EPOCH_SHA256)
        closure = drive / CLOSURE_REL; mc = manifest(closure, CLOSURE_MANIFEST); pp = closure / PRESSURE_EPOCH
        gate("pressure_epoch_SHA_exact", mc.get(PRESSURE_EPOCH) == PRESSURE_EPOCH_SHA256 and sha(pp) == PRESSURE_EPOCH_SHA256)

        with np.load(r22p, allow_pickle=False) as z:
            r22_xyz = np.asarray(z["streamline_xyz_m"], float); r22_tof = np.asarray(z["streamline_tof_s"], float)
            r22_weight = np.asarray(z["streamline_weight_m3_s"], float); r22_producer = np.asarray(z["producer_labels"]).astype("U32")
            r22_id = np.asarray(z["streamline_id"], np.int64)
        with np.load(pp, allow_pickle=False) as z:
            source_pressure = np.asarray(z["refreshed_pressure_psi"], float)
            source_grid_mass = np.asarray(z["pressure_compatible_grid_mass_kg"], float)
            source_p_ref = float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))

        stage = "state_schema_and_source_binding"
        with np.load(state_path, allow_pickle=False) as z:
            required = {
                "canonical_day","source_R25_SCIENTIFIC_FAIL_sha256","source_R25R2_status","stage2_HiGHS_presolve",
                "source_R22_flow_epoch_sha256","source_pressure_epoch_sha256","source_R20_accepted_transport_state_sha256",
                "cartesian_component_mass_kg","transport_CV_component_mass_kg","transport_CV_saturation",
                "grid_residual_component_mass_kg","represented_cartesian_cell_mass_kg","exact_support_edge_cv",
                "exact_support_edge_cell","exact_support_edge_assigned_mass_kg","F1R2_normalized_transpose_edge_target_mass_kg",
                "streamline_xyz_m","streamline_tof_s","streamline_weight_m3_s","producer_labels","streamline_id",
                "refreshed_pressure_psi","reference_gas_pressure_pa","stage1_maximum_representable_mass_kg",
                "stage2_L1_deviation_kg","minimum_unavoidable_S0_residual_kg","outside_S0_residual_kg",
                "global_split_state_ledger_residual_kg","representation_amendment_required","old_CV_cell_ownership_reused",
                "support_growth_executed","reverse_H1_to_S0_pullback_executed","mapback_executed",
                "transport_time_advanced","physical_time_advanced",
            }
            gate("state_required_keys_present", required.issubset(set(z.files)), sorted(required-set(z.files)))
            canonical_day = float(np.asarray(z["canonical_day"]).reshape(()))
            fail_sha_stored = str(np.asarray(z["source_R25_SCIENTIFIC_FAIL_sha256"]).reshape(()))
            stage2_presolve = bool(np.asarray(z["stage2_HiGHS_presolve"]).reshape(()))
            r22_sha_stored = str(np.asarray(z["source_R22_flow_epoch_sha256"]).reshape(()))
            pressure_sha_stored = str(np.asarray(z["source_pressure_epoch_sha256"]).reshape(()))
            r20_sha_stored = str(np.asarray(z["source_R20_accepted_transport_state_sha256"]).reshape(()))
            grid_mass = np.asarray(z["cartesian_component_mass_kg"], float)
            cv_mass = np.asarray(z["transport_CV_component_mass_kg"], float)
            cv_sat = np.asarray(z["transport_CV_saturation"], float)
            residual_grid = np.asarray(z["grid_residual_component_mass_kg"], float)
            represented_grid = np.asarray(z["represented_cartesian_cell_mass_kg"], float)
            edge_cv = np.asarray(z["exact_support_edge_cv"], np.int64).reshape(-1)
            edge_cell = np.asarray(z["exact_support_edge_cell"], np.int64).reshape(-1)
            edge_mass = np.asarray(z["exact_support_edge_assigned_mass_kg"], float).reshape(-1)
            target = np.asarray(z["F1R2_normalized_transpose_edge_target_mass_kg"], float).reshape(-1)
            xyz = np.asarray(z["streamline_xyz_m"], float); tof = np.asarray(z["streamline_tof_s"], float)
            weight = np.asarray(z["streamline_weight_m3_s"], float); producer = np.asarray(z["producer_labels"]).astype("U32")
            streamline_id = np.asarray(z["streamline_id"], np.int64); pressure = np.asarray(z["refreshed_pressure_psi"], float)
            p_ref = float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))
            stage1_stored = float(np.asarray(z["stage1_maximum_representable_mass_kg"]).reshape(()))
            l1_stored = float(np.asarray(z["stage2_L1_deviation_kg"]).reshape(()))
            s0_stored = float(np.asarray(z["minimum_unavoidable_S0_residual_kg"]).reshape(()))
            outside_stored = float(np.asarray(z["outside_S0_residual_kg"]).reshape(()))
            ledger_stored = float(np.asarray(z["global_split_state_ledger_residual_kg"]).reshape(()))
            amendment = bool(np.asarray(z["representation_amendment_required"]).reshape(()))
            old_reuse = bool(np.asarray(z["old_CV_cell_ownership_reused"]).reshape(()))
            support_growth = bool(np.asarray(z["support_growth_executed"]).reshape(()))
            reverse_pull = bool(np.asarray(z["reverse_H1_to_S0_pullback_executed"]).reshape(()))
            mapback = bool(np.asarray(z["mapback_executed"]).reshape(()))
            transport_advance = bool(np.asarray(z["transport_time_advanced"]).reshape(()))
            physical_advance = bool(np.asarray(z["physical_time_advanced"]).reshape(()))

        gate("canonical_day_375", canonical_day == DAY)
        gate("stored_FAIL_SHA_exact", fail_sha_stored == R25_FAIL_SHA256)
        gate("stored_stage2_presolve_false", stage2_presolve is False)
        gate("stored_R22_SHA_exact", r22_sha_stored == R22_EPOCH_SHA256)
        gate("stored_pressure_SHA_exact", pressure_sha_stored == PRESSURE_EPOCH_SHA256)
        gate("stored_R20_SHA_exact", r20_sha_stored == R20_ACCEPTED_STATE_SHA256)
        gate("state_shapes_exact", grid_mass.shape == GRID and cv_mass.shape == (NSL,NCV) and cv_sat.shape == (NSL,NCV) and residual_grid.shape == GRID)
        gate("edge_parallel_lengths_exact", len(edge_cv)==len(edge_cell)==len(edge_mass)==len(target))

        stage = "source_array_identity"
        gate("Cartesian_mass_equals_accepted_pressure_state", np.array_equal(grid_mass, source_grid_mass))
        gate("pressure_array_exact", np.array_equal(pressure, source_pressure))
        gate("reference_pressure_exact", p_ref == source_p_ref)
        gate("R22_geometry_exact", np.array_equal(xyz,r22_xyz) and np.array_equal(tof,r22_tof) and np.array_equal(weight,r22_weight))
        gate("R22_labels_ids_exact", np.array_equal(producer,r22_producer) and np.array_equal(streamline_id,r22_id))

        stage = "exact_support_rebuild"
        sg7d = mod(root / SG7D, "r26_sg7d"); e37a = mod(root / E37A, "r26_e37a"); r2 = mod(root / R2, "r26_r2")
        op = sg7d.build_subsegment_operator(r22_xyz, r22_tof/DAY_TO_S, r22_weight*DAY_TO_S)
        rcv, rcell, rtarget = rebuild_support_target(source_grid_mass, op)
        gate("exact_support_edge_CV_identity", np.array_equal(edge_cv, rcv))
        gate("exact_support_edge_cell_identity", np.array_equal(edge_cell, rcell))
        target_err = float(np.max(np.abs(target-rtarget)))
        gate("F1R2_target_rebuild_match", target_err <= max(1e-9,1e-12*max(float(np.max(np.abs(rtarget))),1.0)), target_err)

        stage = "edge_ledger_reconstruction"
        cell_rebuilt = np.bincount(edge_cell, weights=edge_mass, minlength=NCELL).reshape(GRID)
        cv_rebuilt = np.bincount(edge_cv, weights=edge_mass, minlength=NCVT).reshape(NSL,NCV)
        gate("represented_grid_reconstructed_from_edges", float(np.max(np.abs(cell_rebuilt-represented_grid))) <= MASS_TOL)
        gate("CV_mass_reconstructed_from_edges", float(np.max(np.abs(cv_rebuilt-cv_mass))) <= MASS_TOL)
        residual_rebuilt = grid_mass - represented_grid
        gate("residual_grid_exact_decomposition", float(np.max(np.abs(residual_rebuilt-residual_grid))) <= MASS_TOL)
        gate("residual_grid_nonnegative", float(np.min(residual_grid)) >= -MASS_TOL)
        total_grid, total_cv, total_residual = map(float, [np.sum(grid_mass), np.sum(cv_mass), np.sum(residual_grid)])
        ledger = total_cv + total_residual - total_grid
        gate("global_split_state_ledger_closed", abs(ledger) <= LEDGER_TOL, ledger)
        gate("stored_ledger_matches_rebuilt", abs(ledger-ledger_stored) <= LEDGER_TOL)

        stage = "lexicographic_and_residual_closure"
        stage1 = float(np.sum(edge_mass)); stage1_tol=max(MASS_TOL,OPT_REL_TOL*R24_MAX_REPRESENTABLE_S0_MASS_KG)
        gate("stage1_exact_frontier_preserved", abs(stage1-R24_MAX_REPRESENTABLE_S0_MASS_KG) <= stage1_tol, [stage1,stage1_tol])
        gate("stored_stage1_mass_matches", abs(stage1-stage1_stored) <= stage1_tol)
        l1 = float(np.sum(np.abs(edge_mass-target))); l1_tol=max(1e-6,1e-10*max(abs(l1),1.0))
        gate("stage2_L1_recomputed_matches_stored", abs(l1-l1_stored) <= l1_tol, [l1,l1_stored])
        s0=np.unique(edge_cell); flat_res=residual_grid.reshape(-1); flat_grid=grid_mass.reshape(-1)
        s0_res=float(np.sum(flat_res[s0])); mask=np.ones(NCELL,bool); mask[s0]=False; outside_res=float(np.sum(flat_res[mask])); s0_mass=float(np.sum(flat_grid[s0]))
        s0_tol=max(MASS_TOL,OPT_REL_TOL*R24_MINIMUM_UNAVOIDABLE_S0_RESIDUAL_KG)
        gate("S0_mass_matches_R24", abs(s0_mass-R24_S0_MASS_KG) <= max(MASS_TOL,OPT_REL_TOL*R24_S0_MASS_KG))
        gate("minimum_unavoidable_S0_residual_matches_R24", abs(s0_res-R24_MINIMUM_UNAVOIDABLE_S0_RESIDUAL_KG) <= s0_tol, [s0_res,s0_tol])
        gate("stored_residual_scalars_match", abs(s0_res-s0_stored)<=s0_tol and abs(outside_res-outside_stored)<=MASS_TOL)
        s0_fraction=s0_res/max(s0_mass,1e-30)
        gate("S0_residual_fraction_matches_R24", abs(s0_fraction-R24_MINIMUM_UNAVOIDABLE_S0_RESIDUAL_FRACTION)<=1e-10)

        stage = "CV_capacity_and_saturation_closure"
        geom=e37a.build_control_volume_geometry(r2,op,source_pressure,source_p_ref,NSL,NCV)
        cap=e37a.cv_mass_from_saturation(r2,np.full((NSL,NCV),0.80),geom["cv_pressure_mass_coeff"])
        cap_excess=float(np.max(cv_mass-cap)); gate("CV_capacity_not_exceeded", cap_excess<=CAPACITY_TOL, cap_excess)
        mass_from_sat=e37a.cv_mass_from_saturation(r2,cv_sat,geom["cv_pressure_mass_coeff"])
        sat_mass_err=float(np.max(np.abs(mass_from_sat-cv_mass))); sat_tol=max(1e-6,1e-10*max(float(np.max(cv_mass)),1.0))
        gate("stored_saturation_reconstructs_CV_mass", sat_mass_err<=sat_tol, sat_mass_err)
        gate("stored_saturation_bounds", float(np.min(cv_sat))>=0.20-SAT_TOL and float(np.max(cv_sat))<=0.80+SAT_TOL)
        reinv=e37a.invert_cv_mass_to_saturation(r2,cv_mass,geom["cv_pressure_mass_coeff"])
        reinv_err=float(np.max(np.abs(reinv-cv_sat))); gate("independent_CV_mass_inversion_matches_stored_saturation", reinv_err<=1e-10, reinv_err)

        stage = "representation_firewalls"
        gate("representation_amendment_true", amendment is True)
        gate("old_CV_ownership_not_reused", old_reuse is False)
        gate("support_growth_not_executed", support_growth is False)
        gate("reverse_H1_pullback_not_executed", reverse_pull is False)
        gate("mapback_not_executed", mapback is False)
        gate("transport_time_not_advanced", transport_advance is False)
        gate("physical_time_not_advanced", physical_advance is False)
        gate("summary_P3_false", s25.get("P3_authorized") is False)

        stage = "acceptance_publication"
        state_sha_before=sha(state_path)
        gate("state_SHA_still_exact_before_acceptance", state_sha_before==R25R3_STATE_SHA256)

        classification="R6R26_EXACT_R25R3_CAPACITY_LIMITED_SPLIT_STATE_ACCEPTED_CARTESIAN_PRIMARY_CV_PLUS_RESIDUAL_RESTART_REPRESENTATION_R27_RESIDUAL_TEMPORAL_SEMANTICS_DESIGN_NEXT"
        acceptance={
            "milestone":M,"status":PASS,"accepted_Day375_capacity_limited_split_state":True,
            "accepted_state_file":R25R3_STATE,"accepted_state_sha256":R25R3_STATE_SHA256,
            "accepted_state_source_milestone":"POSTV16-AV4-PIVOT-P2-R6-R25-R3","state_rewritten_by_R26":False,
            "primary_recurrent_authority":"cartesian_component_mass_kg",
            "accepted_transport_coordinate_state":{"component_mass":"transport_CV_component_mass_kg","saturation":"transport_CV_saturation","exact_R22_support_only":True,"capacity_limited":True},
            "accepted_residual_grid_state":{"component_mass":"grid_residual_component_mass_kg","includes_outside_S0_mass":True,"includes_minimum_unavoidable_S0_residual":True,"minimum_unavoidable_S0_residual_kg":s0_res,"outside_S0_residual_kg":outside_res},
            "closure":{"global_split_state_ledger_residual_kg":ledger,"maximum_CV_capacity_excess_kg":max(0.0,cap_excess),"CV_saturation_min":float(np.min(cv_sat)),"CV_saturation_max":float(np.max(cv_sat)),"CV_mass_reconstruction_error_kg":sat_mass_err,"exact_stage1_frontier_mass_kg":stage1,"stage2_L1_deviation_kg":l1},
            "immutable_predecessors":{"R25_SCIENTIFIC_FAIL_sha256":R25_FAIL_SHA256,"R25R2_solver_conditioning_repair_preserved":True,"R24_capacity_limit_preserved":True},
        }
        summary={
            "milestone":M,"name":NAME,"status":PASS,"classification":classification,"accepted_state_sha256":R25R3_STATE_SHA256,"state_rewritten_by_R26":False,
            "source_R22_flow_epoch_sha256":R22_EPOCH_SHA256,"source_pressure_epoch_sha256":PRESSURE_EPOCH_SHA256,"source_R20_accepted_transport_state_sha256":R20_ACCEPTED_STATE_SHA256,"source_R25_SCIENTIFIC_FAIL_sha256":R25_FAIL_SHA256,
            "cartesian_component_mass_total_kg":total_grid,"transport_CV_component_mass_total_kg":total_cv,"grid_residual_component_mass_total_kg":total_residual,
            "S0_residual_mass_kg":s0_res,"S0_residual_fraction_of_S0":s0_fraction,"outside_S0_residual_mass_kg":outside_res,"global_split_state_ledger_residual_kg":ledger,
            "maximum_CV_capacity_excess_kg":max(0.0,cap_excess),"CV_saturation_min":float(np.min(cv_sat)),"CV_saturation_max":float(np.max(cv_sat)),
            "CV_mass_reconstruction_error_kg":sat_mass_err,"independent_saturation_reinversion_error":reinv_err,"stage1_exact_frontier_mass_kg":stage1,"stage2_L1_deviation_kg":l1,
            "representation_accepted":True,"transport_execution_performed":False,"mapback_performed":False,"physical_time_advance_performed":False,"P3_authorized":False,
        }
        decision={
            "milestone":M,"status":PASS,"classification":classification,"R25R3_capacity_limited_split_state_accepted":True,"R25R3_state_sha256":R25R3_STATE_SHA256,
            "accepted_Day375_cartesian_component_mass_remains_primary_authority":True,"accepted_Day375_pressure_epoch_remains_authoritative":True,"R22_flow_geometry_remains_authoritative":True,
            "P2_R6_R27_authorized":True,"P2_R6_R27_name":"Day375 Capacity-Limited Residual / Transport Temporal Semantics Design Freeze","P2_R6_R27_design_only":True,"P2_R6_R27_execution_authorized":False,
            "P2_R6_R27_must_bind_R26_acceptance_contract":True,"P2_R6_R27_must_bind_R25R3_state_SHA":True,"P2_R6_R27_R25R3_state_sha256":R25R3_STATE_SHA256,
            "R27_must_resolve_outside_S0_residual_temporal_semantics":True,"R27_must_resolve_capacity_limited_S0_residual_temporal_semantics":True,
            "transport_execution_authorized_now":False,"mapback_execution_authorized":False,"transport_time_advance_authorized":False,"physical_time_advance_authorized":False,
            "P3_authorized":False,"P4_authorized":False,"P5_training_authorized":False,
        }

        out.mkdir(parents=True, exist_ok=False)
        (out/f"PAD_Stream_{OUT_TOKEN}_Summary.json").write_bytes(jb(summary))
        (out/f"{OUT_TOKEN}_Day375_SplitState_Acceptance_Contract.json").write_bytes(jb(acceptance))
        (out/f"{OUT_TOKEN}_Decision_Contract.json").write_bytes(jb(decision))

        state_sha_after=sha(state_path)
        gate("accepted_R25R3_state_not_rewritten", state_sha_after==state_sha_before==R25R3_STATE_SHA256, [state_sha_before,state_sha_after])

        (out/f"{OUT_TOKEN}_Final_Gate_Matrix.csv").write_bytes(csvb(gates))
        rows=[]
        for p in sorted(out.iterdir()):
            if p.is_file(): rows.append({"file":p.name,"sha256":sha(p),"bytes":p.stat().st_size})
        (out/f"{OUT_TOKEN}_Artifact_Manifest.csv").write_bytes(csvb(rows))

        print("="*190)
        print(M,"PASS")
        print("Accepted R25-R3 state SHA256          :",R25R3_STATE_SHA256)
        print("State rewritten by R26                : False")
        print("Cartesian / CV / residual mass kg     :",total_grid,"/",total_cv,"/",total_residual)
        print("S0 / outside-S0 residual kg           :",s0_res,"/",outside_res)
        print("Global ledger residual kg             :",ledger)
        print("Maximum CV capacity excess kg         :",max(0.0,cap_excess))
        print("CV saturation min / max               :",float(np.min(cv_sat)),"/",float(np.max(cv_sat)))
        print("Stage1 exact frontier / Stage2 L1 kg  :",stage1,"/",l1)
        print("R27 residual temporal semantics       : AUTHORIZED (design only)")
        print("Transport / mapback / time / P3       : False / False / False / False")
        print("="*190)
        return 0

    except Exception as exc:
        block_dir.mkdir(parents=True, exist_ok=True)
        p=block_dir/f"{OUT_TOKEN}_Blocked_Report.json"
        if not p.exists():
            p.write_bytes(jb({"milestone":M,"status":BLOCK,"failed_stage":stage,"exception":repr(exc),"R25R3_state_preserved":True,"R25R3_state_sha256":R25R3_STATE_SHA256,
                              "R25_SCIENTIFIC_FAIL_preserved":True,"R25R2_design_preserved":True,"R24_design_preserved":True,"state_rewrite_executed":False,
                              "transport_execution_executed":False,"mapback_executed":False,"physical_time_advance_executed":False,"P3_authorized":False,
                              "automatic_rerun_authorized":False,"gates_completed":gates}))
        print("="*190); print(M,"TECHNICAL / AUTHORITY BLOCK"); print("Stage:",stage); print("Exception:",repr(exc))
        print("R25-R3 STATE PRESERVED. NO REWRITE / TRANSPORT / MAPBACK / TIME ADVANCE."); print("="*190)
        return 2

if __name__ == "__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--project-root",type=Path,default=Path("."))
    ap.add_argument("--drive-root",type=Path,default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    ap.add_argument("--self-test",action="store_true")
    args=ap.parse_args()
    if args.self_test: selftest(); raise SystemExit(0)
    raise SystemExit(main(args.project_root,args.drive_root))
