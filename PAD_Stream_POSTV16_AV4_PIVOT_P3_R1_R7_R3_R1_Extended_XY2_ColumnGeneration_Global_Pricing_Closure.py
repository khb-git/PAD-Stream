#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, hashlib, importlib.util, io, json, subprocess, sys, time
from pathlib import Path
from typing import Any
import numpy as np

M = "POSTV16-AV4-PIVOT-P3-R1-R7-R3-R1"
NAME = "Extended XY2 Column-Generation Global-Pricing Closure Diagnostic"
PASS = "AV4PIVOTP3R1R7R3R1_EXTENDED_XY2_COLUMN_GENERATION_GLOBAL_PRICING_CLOSURE_PASS_NO_STATE_MUTATION"
BLOCK = "AV4PIVOTP3R1R7R3R1_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "6ba0fb078d5067796b4e9e1649ce42a999624f07"

R7 = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R7_Day375_to_Day380_ThirdObservation_Pilot.py"
R7_BLOB = "0b42bb4cdd395740742e3784f455a2837f3b7ce2"
R7R1R1 = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R7_R1_R1_Corrected_Audit_Lineage_Stage1_XY2_Diagnostic.py"
R7R1R1_BLOB = "3f9a508f5193e83bc62092e8ffd4f8f4f14349be"

R7R2 = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R7_R2_XY2_TerminalOnly_Topology_and_Lexicographic_Design_Freeze.py"
R7R2_BLOB = "52c133f1706287fbf2d1a355875f802a97d80ba4"

R7R3 = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R7_R3_Nominal_XY2_Shadow_Mapback_Global_Pricing_Certification.py"
R7R3_BLOB = "3e5ded576ca4fcdc6c6e1cb7604210a91248b70f"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

R7_STAGE_REL = BASE / "POSTV16_AV4_PIVOT_P3_R1_R7_STAGING"
R7_CHECKPOINT = "POSTV16_AV4_PIVOT_P3_R1_R7_Latest_Recurrent_Checkpoint.npz"
R7_CHECKPOINT_META = "POSTV16_AV4_PIVOT_P3_R1_R7_Latest_Recurrent_Checkpoint.json"
R7_CHECKPOINT_SHA = "d02fef7ef29d273002c1be613539fc39afac1ff231ad369b5f6571b0adcda83b"
R7_PARENT_DAY = 376.9106720614003
R7_ACCEPTED_STEPS = 328

R7R1R1_REL = BASE / "POSTV16_AV4_PIVOT_P3_R1_R7_R1_R1_Corrected_Audit_Lineage_Stage1_Infeasibility_Localization_and_Prospective_XY2_Feasibility_Diagnostic"
R7R1R1_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R7_R1_R1_Summary.json"
R7R1R1_DECISION = "POSTV16_AV4_PIVOT_P3_R1_R7_R1_R1_Decision_Contract.json"
R7R1R1_XY2 = "POSTV16_AV4_PIVOT_P3_R1_R7_R1_R1_Prospective_XY2_Result.json"
R7R1R1_LOCAL = "POSTV16_AV4_PIVOT_P3_R1_R7_R1_R1_Nominal_XY1_Localization.json"
R7R1R1_MANIFEST = "POSTV16_AV4_PIVOT_P3_R1_R7_R1_R1_Artifact_Manifest.csv"
R7R1R1_STATUS = "AV4PIVOTP3R1R7R1R1_CORRECTED_AUDIT_LINEAGE_STAGE1_XY2_DIAGNOSTIC_PASS_NO_STATE_MUTATION"
R7R1R1_CLASS = "P3R1_R7_XY1_POSITIVE_DT_CAPACITY_BOUNDARY_CONFIRMED_PROSPECTIVE_XY2_NOMINAL_STAGE1_FEASIBLE_TOPOLOGY_DESIGN_FREEZE_AUTHORIZED"

R7R2_REL = BASE / "POSTV16_AV4_PIVOT_P3_R1_R7_R2_XY2_TerminalOnly_Topology_and_Lexicographic_Design_Freeze"
R7R2_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R7_R2_Summary.json"
R7R2_DECISION = "POSTV16_AV4_PIVOT_P3_R1_R7_R2_Decision_Contract.json"
R7R2_TOPOLOGY = "POSTV16_AV4_PIVOT_P3_R1_R7_R2_XY2_Topology_Contract.json"
R7R2_LEX = "POSTV16_AV4_PIVOT_P3_R1_R7_R2_Lexicographic_Stage1_Stage2_Contract.json"
R7R2_PRICING = "POSTV16_AV4_PIVOT_P3_R1_R7_R2_Restricted_Master_Dual_Pricing_Contract.json"
R7R2_MANIFEST = "POSTV16_AV4_PIVOT_P3_R1_R7_R2_Artifact_Manifest.csv"
R7R2_STATUS = "AV4PIVOTP3R1R7R2_XY2_TERMINAL_ONLY_TOPOLOGY_LEXICOGRAPHIC_DESIGN_FREEZE_PASS_NO_STATE_MUTATION"
R7R2_CLASS = "P3R1_R7_XY2_TERMINAL_ONLY_SAME_LAYER_TOPOLOGY_AND_FROZEN_LEXICOGRAPHIC_STAGE1_STAGE2_DESIGN_CERTIFIED_NOMINAL_XY2_SHADOW_MAPBACK_AUTHORIZED"

R7R3_REL = BASE / "POSTV16_AV4_PIVOT_P3_R1_R7_R3_Nominal_XY2_Shadow_Mapback_Global_Pricing_Certification"
R7R3_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P3_R1_R7_R3_Summary.json"
R7R3_DECISION = "POSTV16_AV4_PIVOT_P3_R1_R7_R3_Decision_Contract.json"
R7R3_RESULT = "POSTV16_AV4_PIVOT_P3_R1_R7_R3_Stage2_Result.json"
R7R3_AUDIT = "POSTV16_AV4_PIVOT_P3_R1_R7_R3_Column_Generation_Audit.csv"
R7R3_MANIFEST = "POSTV16_AV4_PIVOT_P3_R1_R7_R3_Artifact_Manifest.csv"
R7R3_STATUS = "AV4PIVOTP3R1R7R3_NOMINAL_XY2_SHADOW_MAPBACK_GLOBAL_PRICING_CERTIFICATION_PASS_NO_STATE_MUTATION"
R7R3_CLASS = "P3R1_R7_NOMINAL_XY2_RESTRICTED_STAGE2_SOLVED_BUT_GLOBAL_PRICING_NOT_CLOSED_ADDITIONAL_RUNTIME_DIAGNOSTIC_REQUIRED"
R7R3_EXPECTED_SELECTED_TERMINAL = [29327, 39327, 49327, 59327, 69327]
R7R3_EXPECTED_OBJECTIVE = [
    97824.72765386447,
    59450.67800178237,
    50793.740681623116,
    47513.95530839511,
]
R7R3_EXPECTED_NEGATIVE_COUNT = [47543, 41648, 31178, 21202]
R7R3_EXPECTED_MIN_RC = [-2.0, -2.0, -2.0, -2.0]

MAX_CG_ITERATIONS = 12
COLUMN_BATCH_SIZE = 10000

EXPECTED_EXISTING_EDGE_COUNT = 1245666
EXPECTED_EXISTING_SHELL_EDGE_COUNT = 975945
EXPECTED_XY2_NEW_EDGE_COUNT = 1845407
EXPECTED_TOTAL_EDGE_COUNT = 3091073
EXPECTED_XY2_POSITIVE_NOMINAL_EDGE_COUNT = 9114
EXPECTED_XY2_NOMINAL_ASSIGNED_MASS_KG = 1614134.4851971744
EXPECTED_NOMINAL_TERMINAL_OPT_KG = 2358503.612633198
EXPECTED_XY1_NOMINAL_DEFICIT_KG = 13.989265426676269
EXPECTED_XY1_SMALLEST_DEFICIT_KG = 0.040589185368389735

OUT_TOKEN = "POSTV16_AV4_PIVOT_P3_R1_R7_R3_R1"
OUT_REL = BASE / (OUT_TOKEN + "_Extended_XY2_ColumnGeneration_Global_Pricing_Closure")
BLOCK_REL = BASE / (OUT_TOKEN + "_BLOCKED")
SUMMARY = f"PAD_Stream_{OUT_TOKEN}_Summary.json"
DECISION = f"{OUT_TOKEN}_Decision_Contract.json"
TOPOLOGY = f"{OUT_TOKEN}_XY2_Topology_Audit.json"
LEXICOGRAPHIC = f"{OUT_TOKEN}_Stage2_Result.json"
PRICING = f"{OUT_TOKEN}_Column_Generation_Audit.csv"
COLUMNS = f"{OUT_TOKEN}_Accumulated_Terminal_Columns.npz"
GATES = f"{OUT_TOKEN}_Final_Gate_Matrix.csv"
MANIFEST = f"{OUT_TOKEN}_Artifact_Manifest.csv"

DAY_TO_S = 86400.0
MASS_TOL = 1e-6
HIGHS_FEAS_TOL = 1e-10
HALO_OPT_TOL = 1e-6
PRICING_TOL = 1e-8
POSITIVE_EDGE_TOL = 1e-10

class GateError(RuntimeError):
    pass

def gt(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()

def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()

def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError(f"cannot_load:{path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

def js(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def csvr(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def csvb(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        return b""
    fields: list[str] = []
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    s = io.StringIO(newline="")
    w = csv.DictWriter(s, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return s.getvalue().encode()

def jb(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()

def verify_manifest(directory: Path, filename: str) -> None:
    rows = csvr(directory / filename)
    if not rows:
        raise GateError("manifest_empty")
    for row in rows:
        p = directory / row["file"]
        if not p.is_file():
            raise GateError(f"manifest_missing:{p.name}")
        if sha(p) != row["sha256"]:
            raise GateError(f"manifest_sha:{p.name}")
        if p.stat().st_size != int(row["bytes"]):
            raise GateError(f"manifest_bytes:{p.name}")

def selftest() -> None:
    assert PARENT == "6ba0fb078d5067796b4e9e1649ce42a999624f07"
    assert EXPECTED_TOTAL_EDGE_COUNT == EXPECTED_EXISTING_EDGE_COUNT + EXPECTED_XY2_NEW_EDGE_COUNT
    assert EXPECTED_XY1_NOMINAL_DEFICIT_KG > 0.0
    assert EXPECTED_XY1_SMALLEST_DEFICIT_KG > 0.0
    print("POSTV16 AV4 PIVOT P3-R1-R7-R3-R1 structural self-test: PASS")

def main(project_root: Path, drive_root: Path, time_limit_seconds: float) -> int:
    from scipy.optimize import linprog
    from scipy.sparse import coo_matrix, csr_matrix, eye, hstack, vstack

    root = project_root.resolve()
    drive = drive_root.resolve()
    out = drive / OUT_REL
    blocked = drive / BLOCK_REL
    stage = "preflight"
    gates: list[dict[str, Any]] = []

    def gate(name: str, cond: Any, detail: Any = None) -> None:
        ok = bool(cond)
        gates.append({"stage": stage, "gate": name, "pass": ok, "detail": "" if detail is None else repr(detail)})
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + ("" if detail is None else f" -- {detail}"), flush=True)
        if not ok:
            raise GateError(name)

    try:
        print("=" * 220)
        print("POSTV16-AV4-PIVOT-P3-R1-R7-R3-R1 — EXTENDED XY2 COLUMN-GENERATION GLOBAL-PRICING CLOSURE")
        print("READ-ONLY DETERMINISTIC R7-R3 REPLAY + EXTENDED STAGE2 COLUMN GENERATION. NO STATE/TIME ADVANCE.")
        print("=" * 220)

        stage = "preexisting_state_firewall"
        gate("no_preexisting_PASS", not (out / SUMMARY).exists())
        gate("no_preexisting_BLOCK", not (blocked / f"{OUT_TOKEN}_Blocked_Report.json").exists())

        stage = "repository_authority"
        gate("branch_exact", gt(root, "branch", "--show-current") == BRANCH, gt(root, "branch", "--show-current"))
        gate("parent_is_R7R3_commit", gt(root, "rev-parse", "HEAD^") == PARENT, gt(root, "rev-parse", "HEAD^"))
        gate("repository_clean", gt(root, "status", "--porcelain") == "")
        for fn, blob in [(R7, R7_BLOB), (R7R1R1, R7R1R1_BLOB), (R7R2, R7R2_BLOB), (R7R3, R7R3_BLOB)]:
            fp = root / fn
            gate(f"{Path(fn).stem}_present", fp.is_file(), str(fp))
            gate(f"{Path(fn).stem}_blob_exact", gt(root, "hash-object", str(fp)) == blob, gt(root, "hash-object", str(fp)))

        r7 = load_module(root / R7, "p3r1_r7r2_r7_source")
        p3 = load_module(root / r7.P3R1, "p3r1_r7r2_p3")

        stage = "R7R1R1_authority"
        srcdir = drive / R7R1R1_REL
        gate("R7R1R1_dir_exists", srcdir.is_dir(), str(srcdir))
        for fn in [R7R1R1_SUMMARY, R7R1R1_DECISION, R7R1R1_XY2, R7R1R1_LOCAL, R7R1R1_MANIFEST]:
            gate(f"R7R1R1_artifact_present:{fn}", (srcdir / fn).is_file())
        verify_manifest(srcdir, R7R1R1_MANIFEST)
        s = js(srcdir / R7R1R1_SUMMARY)
        d = js(srcdir / R7R1R1_DECISION)
        xy2_prior = js(srcdir / R7R1R1_XY2)
        local_prior = js(srcdir / R7R1R1_LOCAL)
        gate("R7R1R1_status_exact", s.get("status") == R7R1R1_STATUS, s.get("status"))
        gate("R7R1R1_classification_exact", s.get("classification") == R7R1R1_CLASS, s.get("classification"))
        gate("R7R1R1_design_freeze_authorized", d.get("prospective_XY2_topology_design_freeze_authorized") is True)
        gate("R7R1R1_XY2_execution_locked", d.get("prospective_XY2_execution_authorized") is False)
        gate("R7R1R1_transport_resume_locked", d.get("R7_checkpoint_resume_transport_authorized") is False)
        gate("R7R1R1_Day380_locked", d.get("Day380_repaired_pilot_authorized") is False)
        gate("R7R1R1_full_P3R1_locked", d.get("P3_R1_full_rerun_authorized") is False)
        gate("R7R1R1_P4_locked", d.get("P4_authorized") is False)
        gate("R7R1R1_XY1_nominal_deficit_exact",
             abs(float(local_prior.get("nominal_minimum_added_capacity_kg")) - EXPECTED_XY1_NOMINAL_DEFICIT_KG) <= 1e-9,
             local_prior.get("nominal_minimum_added_capacity_kg"))
        gate("R7R1R1_XY1_smallest_deficit_exact",
             abs(float(local_prior.get("smallest_retry_minimum_added_capacity_kg")) - EXPECTED_XY1_SMALLEST_DEFICIT_KG) <= 1e-9,
             local_prior.get("smallest_retry_minimum_added_capacity_kg"))
        gate("R7R1R1_XY2_nominal_feasible", xy2_prior.get("nominal_stage1_success") is True)
        gate("R7R1R1_XY2_new_edge_count_exact", int(xy2_prior.get("prospective_XY2_new_edge_count")) == EXPECTED_XY2_NEW_EDGE_COUNT)
        gate("R7R1R1_total_edge_count_exact", int(xy2_prior.get("prospective_total_edge_count")) == EXPECTED_TOTAL_EDGE_COUNT)
        gate("R7R1R1_XY2_terminal_only", xy2_prior.get("new_XY2_edges_terminal_only_if_ever_adopted") is True)
        gate("R7R1R1_XY2_same_layer_XY_only", xy2_prior.get("same_layer_XY_face_neighbor_only") is True)

        stage = "R7R2_design_freeze_authority"
        r7r2dir = drive / R7R2_REL
        gate("R7R2_dir_exists", r7r2dir.is_dir(), str(r7r2dir))
        for fn in [R7R2_SUMMARY, R7R2_DECISION, R7R2_TOPOLOGY, R7R2_LEX, R7R2_PRICING, R7R2_MANIFEST]:
            gate(f"R7R2_artifact_present:{fn}", (r7r2dir / fn).is_file())
        verify_manifest(r7r2dir, R7R2_MANIFEST)
        r7r2sum = js(r7r2dir / R7R2_SUMMARY)
        r7r2dec = js(r7r2dir / R7R2_DECISION)
        r7r2top = js(r7r2dir / R7R2_TOPOLOGY)
        r7r2lex = js(r7r2dir / R7R2_LEX)
        r7r2price = js(r7r2dir / R7R2_PRICING)
        gate("R7R2_status_exact", r7r2sum.get("status") == R7R2_STATUS, r7r2sum.get("status"))
        gate("R7R2_classification_exact", r7r2sum.get("classification") == R7R2_CLASS, r7r2sum.get("classification"))
        gate("R7R2_shadow_mapback_authorized", r7r2dec.get("nominal_XY2_shadow_mapback_authorized") is True)
        gate("R7R2_transport_resume_locked", r7r2dec.get("R7_checkpoint_resume_transport_authorized") is False)
        gate("R7R2_XY2_recurrent_execution_locked", r7r2dec.get("XY2_execution_in_recurrent_transport_authorized") is False)
        gate("R7R2_Day380_locked", r7r2dec.get("Day380_repaired_pilot_authorized") is False)
        gate("R7R2_terminal_only_exact", r7r2top.get("XY2_terminal_only") is True and r7r2top.get("XY2_transit_allowed") is False)
        gate("R7R2_no_Z_no_recursive",
             r7r2top.get("z_neighbor_extension") is False and r7r2top.get("recursive_growth") is False)
        gate("R7R2_Stage1_costs_exact",
             float(r7r2lex["Stage1"]["exact_support_cost"]) == 0.0
             and float(r7r2lex["Stage1"]["XY1_terminal_cost"]) == 1.0
             and float(r7r2lex["Stage1"]["XY2_terminal_cost"]) == 1.0)
        gate("R7R2_Stage2_objective_preserved", r7r2lex["Stage2"]["objective_changed_from_R31"] is False)
        gate("R7R2_full_omitted_pricing_required",
             r7r2price.get("omitted_pricing_domain") == "all unselected XY1+XY2 terminal edges")

        stage = "R7R3_runtime_boundary_authority"
        r7r3dir = drive / R7R3_REL
        gate("R7R3_dir_exists", r7r3dir.is_dir(), str(r7r3dir))
        for fn in [R7R3_SUMMARY, R7R3_DECISION, R7R3_RESULT, R7R3_AUDIT, R7R3_MANIFEST]:
            gate(f"R7R3_artifact_present:{fn}", (r7r3dir / fn).is_file())
        verify_manifest(r7r3dir, R7R3_MANIFEST)
        r7r3sum = js(r7r3dir / R7R3_SUMMARY)
        r7r3dec = js(r7r3dir / R7R3_DECISION)
        r7r3res = js(r7r3dir / R7R3_RESULT)
        r7r3audit = csvr(r7r3dir / R7R3_AUDIT)
        gate("R7R3_status_exact", r7r3sum.get("status") == R7R3_STATUS, r7r3sum.get("status"))
        gate("R7R3_classification_exact", r7r3sum.get("classification") == R7R3_CLASS, r7r3sum.get("classification"))
        gate("R7R3_global_not_closed", r7r3res.get("global_optimality_certified") is False)
        gate("R7R3_pricing_valid", r7r3res.get("pricing_valid") is True)
        gate("R7R3_any_restricted_master_success", r7r3res.get("any_restricted_master_success") is True)
        gate("R7R3_five_iterations_recorded", len(r7r3audit) == 5, len(r7r3audit))
        gate("R7R3_first_four_success", all(str(r7r3audit[i].get("solve_success")).lower() == "true" for i in range(4)))
        gate("R7R3_fifth_time_limit",
             str(r7r3audit[4].get("solve_success")).lower() == "false"
             and "Time limit reached" in str(r7r3audit[4].get("solve_message")))
        gate("R7R3_resume_repair_not_authorized", r7r3dec.get("R7_checkpoint_XY2_resume_repair_implementation_authorized") is False)
        gate("R7R3_transport_resume_locked", r7r3dec.get("R7_checkpoint_resume_transport_authorized") is False)
        gate("R7R3_Day380_locked", r7r3dec.get("Day380_repaired_pilot_authorized") is False)

        stage = "checkpoint_authority"
        cp = drive / R7_STAGE_REL / R7_CHECKPOINT
        cpmeta = drive / R7_STAGE_REL / R7_CHECKPOINT_META
        gate("R7_checkpoint_exists", cp.is_file(), str(cp))
        gate("R7_checkpoint_meta_exists", cpmeta.is_file(), str(cpmeta))
        meta = js(cpmeta)
        gate("R7_checkpoint_SHA_exact", sha(cp) == R7_CHECKPOINT_SHA, sha(cp))
        gate("R7_checkpoint_meta_SHA_exact", meta.get("checkpoint_sha256") == R7_CHECKPOINT_SHA, meta.get("checkpoint_sha256"))
        gate("R7_checkpoint_day_exact", abs(float(meta.get("physical_day")) - R7_PARENT_DAY) <= 1e-12, meta.get("physical_day"))
        gate("R7_checkpoint_steps_exact", int(meta.get("accepted_atomic_steps")) == R7_ACCEPTED_STEPS, meta.get("accepted_atomic_steps"))

        stage = "authoritative_inputs"
        a2ep = drive / p3.A2E_REL / p3.A2E_EPOCH
        a6ep = drive / p3.A6E_REL / p3.A6E_STATE
        gate("A2E_epoch_exists", a2ep.is_file(), str(a2ep))
        gate("A2E_epoch_SHA_exact", sha(a2ep) == p3.A2E_EPOCH_SHA, sha(a2ep))
        gate("A6E_state_exists", a6ep.is_file(), str(a6ep))
        gate("A6E_state_SHA_exact", sha(a6ep) == p3.A6E_SHA, sha(a6ep))
        for fn, expected in [
            (p3.A2E, p3.A2E_BLOB), (p3.R2SRC, p3.R2SRC_BLOB),
            (p3.E37A, p3.E37A_BLOB), (p3.SG7A, p3.SG7A_BLOB),
            (p3.SG7D, p3.SG7D_BLOB),
        ]:
            fp = root / fn
            gate(f"{Path(fn).stem}_present", fp.is_file(), str(fp))
            gate(f"{Path(fn).stem}_blob_exact", gt(root, "hash-object", str(fp)) == expected, gt(root, "hash-object", str(fp)))

        a2e = load_module(root / p3.A2E, "p3r1_r7r2_a2e")
        r2src = load_module(root / p3.R2SRC, "p3r1_r7r2_r2src")
        e37a = load_module(root / p3.E37A, "p3r1_r7r2_e37a")
        sg7a = load_module(root / p3.SG7A, "p3r1_r7r2_sg7a")
        sg7d = load_module(root / p3.SG7D, "p3r1_r7r2_sg7d")

        with np.load(a2ep, allow_pickle=False) as z:
            frozen_pressure = np.asarray(z["refreshed_pressure_psi"], dtype=np.float64)
            xyz = np.asarray(z["streamline_xyz_m"], dtype=np.float64)
            tof_s = np.asarray(z["streamline_tof_s"], dtype=np.float64)
            weights_m3_s = np.asarray(z["streamline_weight_m3_s"], dtype=np.float64)
            p_ref = float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))
            tau_end_s = np.asarray(z["tau_end_s"], dtype=np.float64)
        with np.load(a6ep, allow_pickle=False) as z:
            phi = np.asarray(z["paired_porosity"], dtype=np.float64)

        with np.load(cp, allow_pickle=False) as z:
            current_rep = np.asarray(z["represented_cartesian_cell_mass_kg"], dtype=np.float64)
            current_residual = np.asarray(z["grid_residual_component_mass_kg"], dtype=np.float64)
            current_cv_mass = np.asarray(z["transport_CV_component_mass_kg"], dtype=np.float64)
            current_cv_sat = np.asarray(z["transport_CV_saturation"], dtype=np.float64)
            edge_cv = np.asarray(z["XY1_edge_cv"], dtype=np.int64)
            edge_cell = np.asarray(z["XY1_edge_cell"], dtype=np.int64)
            shell = np.asarray(z["XY1_edge_shell_cost"], dtype=np.int8)
            current_edge_mass = np.asarray(z["XY1_edge_assigned_mass_kg"], dtype=np.float64)

        hetero_pv = phi * float(a2e.BULK_VOLUME_M3)
        op = sg7d.build_subsegment_operator(xyz, tof_s / DAY_TO_S, weights_m3_s * DAY_TO_S)
        geometry = e37a.build_control_volume_geometry(r2src, op, frozen_pressure, p_ref, p3.NSL, p3.NCV)
        rho_ref = float(e37a.CO2_RHO_REF_KG_M3)
        sub_pv = np.asarray(geometry["pv_m3"], dtype=np.float64)
        pseg = np.asarray(geometry["pseg_psi"], dtype=np.float64)
        flat_cell = np.asarray(geometry["flat_cell"], dtype=np.int64)
        geom_cv_id = np.asarray(geometry["cv_id"], dtype=np.int64)

        xi_faces = np.linspace(0.0, 1.0, p3.NCV + 1, dtype=np.float64)
        weights_m3_day = weights_m3_s * DAY_TO_S
        sat_scan = np.linspace(float(sg7a.S_INITIAL), float(sg7a.S_INJECTED), 4001)
        max_df = float(np.max(np.abs(np.asarray(sg7a.df_dS(sat_scan), dtype=np.float64))))
        u_face = np.asarray(sg7a.u_dimensionless(xi_faces), dtype=np.float64)
        dtD = float(sg7a.CFL * (1.0 / p3.NCV) / (float(np.max(u_face)) * max_df + float(sg7a.EPS)))
        nominal_dt = float(dtD * np.min(tau_end_s / DAY_TO_S))
        gate("nominal_dt_exact", abs(nominal_dt - 0.03730130768843055) <= 1e-14, nominal_dt)

        full_sat = np.full(p3.GRID, float(a2e.INJECTED), dtype=np.float64)
        cart_capacity = np.asarray(a2e.local_mass(r2src, full_sat, frozen_pressure, p_ref, hetero_pv), dtype=np.float64)
        rep_capacity = cart_capacity - current_residual
        rep_capacity_flat = np.maximum(rep_capacity, 0.0).reshape(-1)

        stage = "XY2_topology_reconstruction"
        gate("existing_edge_count_exact", int(edge_cv.size) == EXPECTED_EXISTING_EDGE_COUNT, int(edge_cv.size))
        gate("existing_terminal_shell_count_exact", int(np.count_nonzero(shell > 0)) == EXPECTED_EXISTING_SHELL_EDGE_COUNT,
             int(np.count_nonzero(shell > 0)))
        gate("existing_shell_binary", set(np.unique(shell).tolist()).issubset({0, 1}), np.unique(shell).tolist())

        shape = tuple(int(v) for v in p3.GRID)
        shell_pos = np.where(shell > 0)[0]
        base_cv = edge_cv[shell_pos]
        base_cell = edge_cell[shell_pos]
        zz, yy, xx = np.unravel_index(base_cell, shape, order="C")
        key_blocks = []
        for dy, dx in [(-1,0),(1,0),(0,-1),(0,1)]:
            yn = yy + dy
            xn = xx + dx
            valid = (yn >= 0) & (yn < shape[1]) & (xn >= 0) & (xn < shape[2])
            if np.any(valid):
                nc = np.ravel_multi_index((zz[valid], yn[valid], xn[valid]), shape, order="C")
                key_blocks.append(base_cv[valid].astype(np.int64) * np.int64(p3.NCELL) + nc.astype(np.int64))
        candidate_keys = np.unique(np.concatenate(key_blocks))
        existing_keys = np.unique(edge_cv.astype(np.int64) * np.int64(p3.NCELL) + edge_cell.astype(np.int64))
        new_keys = np.setdiff1d(candidate_keys, existing_keys, assume_unique=True)
        xy2_cv = (new_keys // np.int64(p3.NCELL)).astype(np.int64)
        xy2_cell = (new_keys % np.int64(p3.NCELL)).astype(np.int64)
        ext_cv = np.concatenate([edge_cv, xy2_cv])
        ext_cell = np.concatenate([edge_cell, xy2_cell])
        ext_shell = np.concatenate([shell, np.ones(xy2_cv.size, dtype=np.int8)])

        gate("XY2_new_edge_count_exact", int(xy2_cv.size) == EXPECTED_XY2_NEW_EDGE_COUNT, int(xy2_cv.size))
        gate("XY2_total_edge_count_exact", int(ext_cv.size) == EXPECTED_TOTAL_EDGE_COUNT, int(ext_cv.size))
        gate("XY2_new_edges_unique", int(np.unique(new_keys).size) == int(new_keys.size))
        gate("XY2_new_edges_disjoint_existing", np.intersect1d(new_keys, existing_keys).size == 0)
        gate("XY2_new_shell_cost_one", bool(np.all(ext_shell[edge_cv.size:] == 1)))
        gate("exact_support_cost_zero_preserved", bool(np.all(ext_shell[:edge_cv.size][shell == 0] == 0)))
        gate("existing_XY1_terminal_cost_one_preserved", bool(np.all(ext_shell[:edge_cv.size][shell > 0] == 1)))

        # Transport support is unchanged: every mapped subsegment remains exact support, and XY2 is representation-only.
        edge_keys = edge_cv.astype(np.int64) * np.int64(p3.NCELL) + edge_cell.astype(np.int64)
        key_to_shell = {int(k): int(v) for k, v in zip(edge_keys.tolist(), shell.tolist())}
        sub_cv = np.asarray(op["streamline"], dtype=np.int64) * p3.NCV + np.asarray(op["node"], dtype=np.int64)
        sub_cell = np.asarray(op["flat_cell"], dtype=np.int64)
        sub_keys = sub_cv.astype(np.int64) * np.int64(p3.NCELL) + sub_cell.astype(np.int64)
        gate("all_transport_subsegments_remain_existing_exact_support",
             all(key_to_shell.get(int(k), -1) == 0 for k in sub_keys.tolist()))
        gate("no_transport_subsegment_uses_XY2", np.intersect1d(np.unique(sub_keys), new_keys).size == 0)

        stage = "nominal_candidate_reconstruction"
        theory_flux = np.zeros((p3.NSL, p3.NCV + 1), dtype=np.float64)
        theory_flux[:, 0] = weights_m3_day * rho_ref
        ff_internal = np.asarray(sg7a.fractional_flow(current_cv_sat[:, :-1]), dtype=np.float64)
        theory_flux[:, 1:-1] = weights_m3_day[:, None] * u_face[None, 1:-1] * ff_internal * rho_ref
        ff_out = np.asarray(sg7a.fractional_flow(current_cv_sat[:, -1]), dtype=np.float64)
        theory_flux[:, -1] = weights_m3_day * float(u_face[-1]) * ff_out * rho_ref
        nominal_demand = current_cv_mass + nominal_dt * (theory_flux[:, :-1] - theory_flux[:, 1:])
        gate("nominal_candidate_CV_nonnegative", float(np.min(nominal_demand)) >= -MASS_TOL, float(np.min(nominal_demand)))

        new_cv_sat = np.asarray(
            e37a.invert_cv_mass_to_saturation(r2src, nominal_demand, geometry["cv_pressure_mass_coeff"]),
            dtype=np.float64,
        )
        old_sub_sat = current_cv_sat.reshape(-1)[geom_cv_id]
        new_sub_sat = new_cv_sat.reshape(-1)[geom_cv_id]
        old_sub_sg = np.clip(old_sub_sat - p3.BACKGROUND, 0.0, p3.MAX_SG)
        new_sub_sg = np.clip(new_sub_sat - p3.BACKGROUND, 0.0, p3.MAX_SG)
        rho_old = np.asarray(r2src.gas_density_from_state(old_sub_sat, pseg, p_ref), dtype=np.float64)
        rho_new = np.asarray(r2src.gas_density_from_state(new_sub_sat, pseg, p_ref), dtype=np.float64)
        sub_delta = sub_pv * (rho_new * new_sub_sg - rho_old * old_sub_sg)
        cv_delta = float(np.sum(nominal_demand) - np.sum(current_cv_mass))
        gate("subsegment_delta_closure", abs(float(np.sum(sub_delta)) - cv_delta) <= MASS_TOL,
             float(np.sum(sub_delta)) - cv_delta)
        delta_grid = np.bincount(flat_cell, weights=sub_delta, minlength=p3.NCELL).reshape(p3.GRID)
        direct_target_rep = current_rep + delta_grid
        target_flat = direct_target_rep.reshape(-1)

        stage = "nominal_Stage1_shadow"
        ne = int(ext_cv.size)
        ii = np.arange(ne, dtype=np.int64)
        Aeq = coo_matrix((np.ones(ne), (ext_cv, ii)), shape=(p3.NCVT, ne)).tocsr()
        Acell = coo_matrix((np.ones(ne), (ext_cell, ii)), shape=(p3.NCELL, ne)).tocsr()
        c1 = (ext_shell > 0).astype(np.float64)
        t0 = time.perf_counter()
        lp1 = linprog(
            c1, A_ub=Acell, b_ub=rep_capacity_flat,
            A_eq=Aeq, b_eq=nominal_demand.reshape(-1),
            bounds=(0.0, None), method="highs-ds",
            options={
                "presolve": True,
                "primal_feasibility_tolerance": HIGHS_FEAS_TOL,
                "dual_feasibility_tolerance": HIGHS_FEAS_TOL,
                "time_limit": float(time_limit_seconds),
            },
        )
        stage1_wall = time.perf_counter() - t0
        gate("XY2_nominal_Stage1_success", lp1.success, [lp1.status, lp1.message])
        halo_opt = float(lp1.fun)
        x1 = np.asarray(lp1.x, dtype=np.float64)
        gate("XY2_nominal_terminal_optimum_matches_prior",
             abs(halo_opt - EXPECTED_NOMINAL_TERMINAL_OPT_KG) <= 2e-6,
             [halo_opt, EXPECTED_NOMINAL_TERMINAL_OPT_KG])
        positive_xy2 = int(np.count_nonzero(x1[edge_cv.size:] > POSITIVE_EDGE_TOL))
        assigned_xy2 = float(np.sum(x1[edge_cv.size:]))
        gate("XY2_nominal_positive_new_edge_count_matches_prior",
             positive_xy2 == EXPECTED_XY2_POSITIVE_NOMINAL_EDGE_COUNT,
             positive_xy2)
        gate("XY2_nominal_assigned_mass_matches_prior",
             abs(assigned_xy2 - EXPECTED_XY2_NOMINAL_ASSIGNED_MASS_KG) <= 2e-6,
             [assigned_xy2, EXPECTED_XY2_NOMINAL_ASSIGNED_MASS_KG])

        stage = "nominal_Stage2_shadow_column_generation"
        exact_positions = np.where(ext_shell == 0)[0]
        terminal_mask = ext_shell > 0
        stage1_positive_terminal = np.where(terminal_mask & (x1 > POSITIVE_EDGE_TOL))[0]
        prior_positive_xy1 = np.where(
            (np.arange(ext_cv.size) < edge_cv.size)
            & terminal_mask
            & (np.concatenate([current_edge_mass, np.zeros(xy2_cv.size)]) > POSITIVE_EDGE_TOL)
        )[0]
        initial_terminal = np.unique(np.concatenate([stage1_positive_terminal, prior_positive_xy1]))
        selected_terminal = set(int(x) for x in initial_terminal.tolist())

        cg_rows: list[dict[str, Any]] = []
        cg_global_certified = False
        pricing_valid = True
        final_lp = None
        final_positions = None
        final_min_rc = None
        total_stage2_wall = 0.0

        for cg_iter in range(1, MAX_CG_ITERATIONS + 1):
            selected_positions = np.unique(np.concatenate([
                exact_positions,
                np.asarray(sorted(selected_terminal), dtype=np.int64),
            ]))
            nsel = int(selected_positions.size)
            sel_cv = ext_cv[selected_positions]
            sel_cell = ext_cell[selected_positions]
            sel_shell = ext_shell[selected_positions]
            sel_idx = np.arange(nsel, dtype=np.int64)

            Aeq_sel = coo_matrix(
                (np.ones(nsel, dtype=np.float64), (sel_cv, sel_idx)),
                shape=(p3.NCVT, nsel),
            ).tocsr()
            Acell_sel = coo_matrix(
                (np.ones(nsel, dtype=np.float64), (sel_cell, sel_idx)),
                shape=(p3.NCELL, nsel),
            ).tocsr()

            nd = p3.NCELL
            I = eye(nd, format="csr", dtype=np.float64)
            zero_d = csr_matrix((p3.NCELL, nd), dtype=np.float64)
            A_cap = hstack([Acell_sel, zero_d], format="csr")
            A_abs_pos = hstack([Acell_sel, -I], format="csr")
            A_abs_neg = hstack([-Acell_sel, -I], format="csr")
            halo_row = csr_matrix((sel_shell > 0).astype(np.float64).reshape(1, -1))
            zero1 = csr_matrix((1, nd), dtype=np.float64)
            A_halo_pos = hstack([halo_row, zero1], format="csr")
            A_halo_neg = hstack([-halo_row, zero1], format="csr")
            A_ub2 = vstack([A_cap, A_abs_pos, A_abs_neg, A_halo_pos, A_halo_neg], format="csr")
            b_ub2 = np.concatenate([
                rep_capacity_flat,
                target_flat,
                -target_flat,
                np.asarray([halo_opt + HALO_OPT_TOL, -halo_opt + HALO_OPT_TOL], dtype=np.float64),
            ])
            Aeq2 = hstack([Aeq_sel, csr_matrix((p3.NCVT, nd), dtype=np.float64)], format="csr")
            c2 = np.concatenate([np.zeros(nsel), np.ones(nd)])
            bounds2 = [(0.0, None)] * (nsel + nd)

            t2 = time.perf_counter()
            lp2 = linprog(
                c2,
                A_ub=A_ub2,
                b_ub=b_ub2,
                A_eq=Aeq2,
                b_eq=nominal_demand.reshape(-1),
                bounds=bounds2,
                method="highs-ds",
                options={
                    "presolve": True,
                    "primal_feasibility_tolerance": HIGHS_FEAS_TOL,
                    "dual_feasibility_tolerance": HIGHS_FEAS_TOL,
                    "time_limit": float(time_limit_seconds),
                },
            )
            wall = time.perf_counter() - t2
            total_stage2_wall += wall

            row = {
                "iteration": cg_iter,
                "selected_edge_count": nsel,
                "selected_terminal_edge_count": int(np.count_nonzero(sel_shell > 0)),
                "solve_success": bool(lp2.success),
                "solve_status": int(lp2.status),
                "solve_message": str(lp2.message),
                "solve_wall_seconds": wall,
                "objective_L1_kg": float(lp2.fun) if lp2.success else None,
            }
            final_lp = lp2
            final_positions = selected_positions

            if not lp2.success:
                row.update({
                    "pricing_validation_error": None,
                    "omitted_terminal_count": None,
                    "minimum_omitted_reduced_cost": None,
                    "negative_omitted_count": None,
                    "columns_added": None,
                    "global_optimality_certified": False,
                })
                cg_rows.append(row)
                break

            mu = np.asarray(lp2.ineqlin.marginals, dtype=np.float64)
            lam = np.asarray(lp2.eqlin.marginals, dtype=np.float64)
            lower = np.asarray(lp2.lower.marginals, dtype=np.float64)

            mu_cap = mu[0:p3.NCELL]
            mu_pos = mu[p3.NCELL:2*p3.NCELL]
            mu_neg = mu[2*p3.NCELL:3*p3.NCELL]
            mu_hpos = float(mu[3*p3.NCELL])
            mu_hneg = float(mu[3*p3.NCELL + 1])

            predicted_selected = -(
                mu_cap[sel_cell]
                + mu_pos[sel_cell]
                - mu_neg[sel_cell]
                + (sel_shell > 0).astype(np.float64) * (mu_hpos - mu_hneg)
            ) - lam[sel_cv]
            pricing_error = float(np.max(np.abs(predicted_selected - lower[:nsel])))
            if pricing_error > 1e-7:
                pricing_valid = False
                row.update({
                    "pricing_validation_error": pricing_error,
                    "omitted_terminal_count": None,
                    "minimum_omitted_reduced_cost": None,
                    "negative_omitted_count": None,
                    "columns_added": None,
                    "global_optimality_certified": False,
                })
                cg_rows.append(row)
                break

            selected_terminal_mask = np.zeros(ne, dtype=bool)
            if selected_terminal:
                selected_terminal_mask[np.asarray(sorted(selected_terminal), dtype=np.int64)] = True
            omitted_positions = np.where(terminal_mask & (~selected_terminal_mask))[0]

            if omitted_positions.size:
                ocell = ext_cell[omitted_positions]
                ocv = ext_cv[omitted_positions]
                omitted_rc = -(
                    mu_cap[ocell]
                    + mu_pos[ocell]
                    - mu_neg[ocell]
                    + (mu_hpos - mu_hneg)
                ) - lam[ocv]
                min_rc = float(np.min(omitted_rc))
                negative_local = np.where(omitted_rc < -PRICING_TOL)[0]
            else:
                omitted_rc = np.asarray([], dtype=np.float64)
                min_rc = float("inf")
                negative_local = np.asarray([], dtype=np.int64)

            final_min_rc = min_rc
            row.update({
                "pricing_validation_error": pricing_error,
                "omitted_terminal_count": int(omitted_positions.size),
                "minimum_omitted_reduced_cost": min_rc,
                "negative_omitted_count": int(negative_local.size),
            })

            if cg_iter <= 4:
                gate(f"R7R3_replay_iter{cg_iter}_selected_terminal_exact",
                     int(row["selected_terminal_edge_count"]) == R7R3_EXPECTED_SELECTED_TERMINAL[cg_iter - 1],
                     row["selected_terminal_edge_count"])
                gate(f"R7R3_replay_iter{cg_iter}_objective_match",
                     abs(float(row["objective_L1_kg"]) - R7R3_EXPECTED_OBJECTIVE[cg_iter - 1]) <= 1e-5,
                     [row["objective_L1_kg"], R7R3_EXPECTED_OBJECTIVE[cg_iter - 1]])
                gate(f"R7R3_replay_iter{cg_iter}_negative_count_exact",
                     int(row["negative_omitted_count"]) == R7R3_EXPECTED_NEGATIVE_COUNT[cg_iter - 1],
                     row["negative_omitted_count"])
                gate(f"R7R3_replay_iter{cg_iter}_minimum_rc_exact",
                     abs(float(row["minimum_omitted_reduced_cost"]) - R7R3_EXPECTED_MIN_RC[cg_iter - 1]) <= 1e-12,
                     row["minimum_omitted_reduced_cost"])

            if cg_iter == 5:
                gate("R7R3_replay_iter5_selected_terminal_exact",
                     int(row["selected_terminal_edge_count"]) == R7R3_EXPECTED_SELECTED_TERMINAL[4],
                     row["selected_terminal_edge_count"])

            if negative_local.size == 0:
                cg_global_certified = True
                row["columns_added"] = 0
                row["global_optimality_certified"] = True
                cg_rows.append(row)
                break

            order = negative_local[np.argsort(omitted_rc[negative_local])]
            take = order[:COLUMN_BATCH_SIZE]
            add_positions = omitted_positions[take]
            for pos in add_positions.tolist():
                selected_terminal.add(int(pos))
            row["columns_added"] = int(add_positions.size)
            row["most_negative_added"] = float(np.min(omitted_rc[take])) if take.size else None
            row["global_optimality_certified"] = False
            cg_rows.append(row)

        stage = "nominal_Stage2_validation"
        any_restricted_master_success = any(bool(r["solve_success"]) for r in cg_rows)
        stage2_validation = {
            "global_optimality_certified": False,
            "pricing_valid": pricing_valid,
            "any_restricted_master_success": any_restricted_master_success,
            "initial_terminal_seed_count": int(initial_terminal.size),
            "Stage1_positive_terminal_edge_count": int(stage1_positive_terminal.size),
            "prior_accepted_positive_XY1_edge_count": int(prior_positive_xy1.size),
            "final_selected_terminal_edge_count": int(len(selected_terminal)),
            "column_generation_iterations": len(cg_rows),
            "total_Stage2_wall_seconds": total_stage2_wall,
            "final_minimum_omitted_reduced_cost": final_min_rc,
        }

        if (
            cg_global_certified
            and pricing_valid
            and final_lp is not None
            and final_lp.success
            and final_positions is not None
        ):
            nsel = int(final_positions.size)
            z2 = np.asarray(final_lp.x, dtype=np.float64)
            x2 = z2[:nsel]
            d2 = z2[nsel:]
            sel_cv = ext_cv[final_positions]
            sel_cell = ext_cell[final_positions]
            sel_shell = ext_shell[final_positions]

            rep_flat = np.bincount(sel_cell, weights=x2, minlength=p3.NCELL)
            cv_check = np.bincount(sel_cv, weights=x2, minlength=p3.NCVT).reshape(p3.NSL, p3.NCV)
            cv_err = float(np.max(np.abs(cv_check - nominal_demand)))
            aux_err = float(np.max(np.abs(d2 - np.abs(rep_flat - target_flat))))
            terminal_mass = float(np.sum(x2[sel_shell > 0]))
            l1 = float(np.sum(np.abs(rep_flat - target_flat)))
            capacity_excess = float(np.max(rep_flat - rep_capacity_flat))
            rep_min = float(np.min(rep_flat))
            objective_gap = abs(float(final_lp.fun) - l1)

            gate("Stage2_CV_equality", cv_err <= MASS_TOL, cv_err)
            gate("Stage2_terminal_mass_matches_Stage1",
                 abs(terminal_mass - halo_opt) <= 2.0 * HALO_OPT_TOL,
                 [terminal_mass, halo_opt])
            gate("Stage2_auxiliary_exact", aux_err <= 1e-5, aux_err)
            gate("Stage2_objective_matches_recomputed_L1",
                 objective_gap <= max(1e-5, 1e-10 * max(l1, 1.0)),
                 [float(final_lp.fun), l1])
            gate("Stage2_capacity", capacity_excess <= max(1e-8, 1e-12 * max(float(np.max(rep_capacity_flat)), 1.0)),
                 capacity_excess)
            gate("Stage2_nonnegative_representation", rep_min >= -MASS_TOL, rep_min)

            selected_xy2_mask = final_positions >= edge_cv.size
            selected_xy2_positions = final_positions[selected_xy2_mask]
            selected_xy2_mass = x2[selected_xy2_mask]
            stage2_validation.update({
                "global_optimality_certified": True,
                "CV_equality_max_abs_error_kg": cv_err,
                "auxiliary_max_abs_error_kg": aux_err,
                "terminal_mass_kg": terminal_mass,
                "Stage1_terminal_optimum_kg": halo_opt,
                "terminal_optimum_gap_kg": terminal_mass - halo_opt,
                "L1_recomputed_kg": l1,
                "solver_objective_kg": float(final_lp.fun),
                "objective_gap_kg": objective_gap,
                "Cartesian_capacity_excess_kg": capacity_excess,
                "Cartesian_min_represented_mass_kg": rep_min,
                "positive_selected_XY2_edge_count": int(np.count_nonzero(selected_xy2_mass > POSITIVE_EDGE_TOL)),
                "selected_XY2_assigned_mass_kg": float(np.sum(selected_xy2_mass)),
            })

        if stage2_validation["global_optimality_certified"]:
            classification = "P3R1_R7_EXTENDED_XY2_COLUMN_GENERATION_GLOBAL_LEXICOGRAPHIC_OPTIMUM_CERTIFIED_R7_CHECKPOINT_XY2_RESUME_REPAIR_IMPLEMENTATION_AUTHORIZED"
            recommendation = (
                "Implement a restart-safe R7 checkpoint resume repair from Day 376.9106720614003 using the frozen XY2 terminal-only "
                "support, unchanged Stage1/Stage2 lexicographic objectives, carry-forward XY1/XY2 terminal seeding, and full omitted "
                "XY1+XY2 dual pricing. Do not restart from Day375."
            )
            resume_repair_authorized = True
        elif any_restricted_master_success and pricing_valid:
            classification = "P3R1_R7_EXTENDED_XY2_RESTRICTED_STAGE2_SOLVED_BUT_GLOBAL_PRICING_NOT_CLOSED_ACCUMULATED_COLUMNS_PRESERVED_FURTHER_BOUNDED_DIAGNOSTIC_REQUIRED"
            recommendation = (
                "Preserve the R7 checkpoint and extend the bounded XY2 column-generation diagnostic using the accumulated columns; "
                "do not authorize recurrent XY2 execution yet."
            )
            resume_repair_authorized = False
        else:
            classification = "P3R1_R7_EXTENDED_XY2_STAGE2_RUNTIME_OR_PRICING_VALIDATION_BOUNDARY_ACCUMULATED_COLUMNS_PRESERVED"
            recommendation = (
                "Preserve the R7 checkpoint and localize the XY2 Stage2 restricted-master or pricing failure; "
                "do not authorize recurrent XY2 execution."
            )
            resume_repair_authorized = False

        topology_audit = {
            "XY2_terminal_only": True,
            "XY2_transit_allowed": False,
            "same_layer_XY_face_neighbor_only": True,
            "nonrecursive_single_additional_ring": True,
            "new_XY2_edge_count": int(xy2_cv.size),
            "total_edge_count": int(ext_cv.size),
            "exact_support_edge_count": int(np.count_nonzero(ext_shell == 0)),
            "terminal_edge_count": int(np.count_nonzero(ext_shell > 0)),
            "transport_subsegment_mapping_changed": False,
            "physics_changed": False,
            "CFL_changed": False,
        }

        stage = "publication"
        out.mkdir(parents=True, exist_ok=False)
        (out / TOPOLOGY).write_bytes(jb(topology_audit))
        (out / LEXICOGRAPHIC).write_bytes(jb(stage2_validation))
        (out / PRICING).write_bytes(csvb(cg_rows))
        np.savez_compressed(
            out / COLUMNS,
            selected_terminal_positions=np.asarray(sorted(selected_terminal), dtype=np.int64),
            exact_positions=np.asarray(exact_positions, dtype=np.int64),
            Stage1_positive_terminal_positions=np.asarray(stage1_positive_terminal, dtype=np.int64),
            prior_accepted_positive_XY1_positions=np.asarray(prior_positive_xy1, dtype=np.int64),
            total_edge_count=np.asarray([ne], dtype=np.int64),
        )
        (out / GATES).write_bytes(csvb(gates))

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": classification,
            "repository_parent_R7R3_commit": PARENT,
            "R7_checkpoint_sha256": R7_CHECKPOINT_SHA,
            "R7_checkpoint_day": R7_PARENT_DAY,
            "R7_checkpoint_accepted_steps": R7_ACCEPTED_STEPS,
            "R7R2_status_bound": R7R2_STATUS,
            "R7R3_status_bound": R7R3_STATUS,
            "R7R3_classification_bound": R7R3_CLASS,
            "R7R3_first_four_iterations_deterministically_replayed": True,
            "accumulated_terminal_columns_file": COLUMNS,
            "R7R2_classification_bound": R7R2_CLASS,
            "authoritative_physics_state_mutated": False,
            "authoritative_physical_time_advanced": False,
            "XY2_new_edge_count": int(xy2_cv.size),
            "XY2_total_edge_count": int(ext_cv.size),
            "nominal_Stage1_terminal_mass_optimum_kg": halo_opt,
            "nominal_Stage1_wall_seconds": stage1_wall,
            "Stage2_result": stage2_validation,
            "global_Stage2_optimality_certified": bool(stage2_validation["global_optimality_certified"]),
            "R7_checkpoint_XY2_resume_repair_implementation_authorized": bool(resume_repair_authorized),
            "XY2_execution_in_recurrent_transport_authorized": False,
            "R7_checkpoint_resume_transport_authorized": False,
            "Day380_repaired_pilot_authorized": False,
            "P3_R1_full_rerun_authorized": False,
            "P4_authorized": False,
            "physics_change_authorized": False,
            "CFL_change_authorized": False,
            "residual_sidecar_change_authorized": False,
            "lexicographic_objective_change_authorized": False,
            "recommended_next_action": recommendation,
        }
        decision = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "R32_recurrent_semantics_remain_authoritative": True,
            "R7_checkpoint_must_be_preserved": True,
            "restart_from_Day375_authorized": False,
            "XY2_topology_design_remains_frozen": True,
            "R7R3_runtime_boundary_closed_as_bounded_solver_time_limit": True,
            "accumulated_terminal_columns_published": True,
            "Stage1_exact_cost_zero": True,
            "Stage1_XY1_and_XY2_terminal_cost_equal_one": True,
            "Stage2_full_Cartesian_L1_objective_preserved": True,
            "Stage2_full_omitted_XY1_XY2_dual_pricing_required": True,
            "global_Stage2_optimality_certified": bool(stage2_validation["global_optimality_certified"]),
            "R7_checkpoint_XY2_resume_repair_implementation_authorized": bool(resume_repair_authorized),
            "XY2_execution_in_recurrent_transport_authorized": False,
            "R7_checkpoint_resume_transport_authorized": False,
            "Day380_repaired_pilot_authorized": False,
            "P3_R1_full_rerun_authorized": False,
            "P4_authorized": False,
            "physics_change_authorized": False,
            "CFL_change_authorized": False,
            "residual_sidecar_change_authorized": False,
            "lexicographic_objective_change_authorized": False,
            "recommended_next_action": recommendation,
        }
        (out / SUMMARY).write_bytes(jb(summary))
        (out / DECISION).write_bytes(jb(decision))
        mr = []
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name != MANIFEST:
                mr.append({"file": p.name, "sha256": sha(p), "bytes": p.stat().st_size})
        (out / MANIFEST).write_bytes(csvb(mr))

        print("=" * 220)
        print(M, "PASS")
        print("Classification:", classification)
        print("Stage1 terminal optimum kg:", halo_opt)
        print("Stage2 global optimum certified:", stage2_validation["global_optimality_certified"])
        print("CG iterations:", len(cg_rows))
        print("Final omitted minimum reduced cost:", final_min_rc)
        print("R7 XY2 resume-repair implementation authorized:", resume_repair_authorized)
        print("R7 recurrent transport execution authorized: False")
        print("Day380 pilot authorized: False")
        print("P4 authorized: False")
        print("=" * 220)
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        rp = blocked / f"{OUT_TOKEN}_Blocked_Report.json"
        if not rp.exists():
            rp.write_bytes(jb({
                "milestone": M,
                "status": BLOCK,
                "failed_stage": stage,
                "exception": repr(exc),
                "authoritative_physics_state_mutated": False,
                "authoritative_physical_time_advanced": False,
                "R7_checkpoint_XY2_resume_repair_implementation_authorized": False,
                "R7_checkpoint_resume_transport_authorized": False,
                "Day380_repaired_pilot_authorized": False,
                "P3_R1_full_rerun_authorized": False,
                "P4_authorized": False,
                "gates_completed": gates,
            }))
        print(M, "TECHNICAL / AUTHORITY BLOCK")
        print("Stage:", stage)
        print("Exception:", repr(exc))
        return 2

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", type=Path, default=Path("."))
    ap.add_argument("--drive-root", type=Path, default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    ap.add_argument("--time-limit-seconds", type=float, default=120.0)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        selftest()
        raise SystemExit(0)
    raise SystemExit(main(args.project_root, args.drive_root, args.time_limit_seconds))
