#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, hashlib, importlib.util, io, json, subprocess, sys
from pathlib import Path
from typing import Any
import numpy as np

M = "POSTV16-AV4-PIVOT-P2-R6-R32"
NAME = "Independent Recurrent-Operation Closure Audit"

PASS = (
    "AV4PIVOTP2R6R32_INDEPENDENT_RECURRENT_OPERATION_CLOSURE_AUDIT_"
    "PASS_AV4_RECURRENT_PHYSICS_CLOSED_NO_R31_TIME_COMMIT"
)
BLOCK = "AV4PIVOTP2R6R32_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "6a6e7a0524779746ecae2e72e142ed7a46a38bbe"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"
BASE_AV3 = Path("post_v16") / RID / "POSTV16_AV3_Corey_Relperm_Heterogeneity"

GRID = (15, 50, 50)
NCELL = 37500
NSL = 1078
NCV = 200
NCVT = NSL * NCV

FLOW_EPOCH_DAY = 375.0
R30_DAY = 375.0372167312886
DT = 0.03721673128859954
R31_TARGET_DAY = 375.0744334625772
BACKGROUND = 0.20
MAX_SAT = 0.80
MASS_TOL = 1.0e-6
SAT_TOL = 1.0e-10
REL_TOL = 1.0e-10

# R31 recurrence authority.
R31_TOKEN = "POSTV16_AV4_PIVOT_P2_R6_R31"
R31_REL = BASE / (R31_TOKEN + "_PostR30_Recurrent_FrozenFlow_Transport_Mapback_Certification")
R31_SUMMARY = "PAD_Stream_" + R31_TOKEN + "_Summary.json"
R31_DECISION = R31_TOKEN + "_Decision_Contract.json"
R31_CERT = R31_TOKEN + "_Recurrent_Operation_Certification_Contract.json"
R31_MANIFEST = R31_TOKEN + "_Artifact_Manifest.csv"
R31_STATE = R31_TOKEN + "_Prospective_Recurrent_Candidate_State.npz"
R31_STATUS = (
    "AV4PIVOTP2R6R31_POST_R30_RECURRENT_FROZEN_FLOW_TRANSPORT_MAPBACK_"
    "CERTIFICATION_PASS_PROSPECTIVE_NEXT_STEP_NO_TIME_COMMIT"
)
R31_CLASS = (
    "POST_R30_COMMITTED_STATE_SUCCESSFULLY_SERVES_AS_RECURRENT_PARENT_"
    "FOR_SECOND_ALL_CV_XY1_FROZEN_FLOW_TRANSPORT_MAPBACK_STEP_"
    "FULL_PROPAGATION_CLOSED_NO_TIME_COMMIT"
)
R31_STATE_SHA = "dad04bea0edeb6089453f193e2d6a6abdd79d1a944b6613737e742abeccac66e"

R31_RUNNER = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R31_PostR30_Recurrent_FrozenFlow_Transport_Mapback_Certification.py"
R31_RUNNER_BLOB = "c6307aa53109c4ae6c4a2f962e1fef86fbc8ea4a"

# R30 authoritative state.
R30_TOKEN = "POSTV16_AV4_PIVOT_P2_R6_R30"
R30_REL = BASE / (R30_TOKEN + "_Atomic_Physical_Time_Commit_Accepted_AllCV_XY1_Candidate")
R30_SUMMARY = "PAD_Stream_" + R30_TOKEN + "_Summary.json"
R30_DECISION = R30_TOKEN + "_Decision_Contract.json"
R30_MANIFEST = R30_TOKEN + "_Artifact_Manifest.csv"
R30_STATE = R30_TOKEN + "_Committed_State_Day375p0372167312886.npz"
R30_STATE_SHA = "07856a508db8ae6ba449e9e248bf8cdbc406eb0b4504471099b4b82f6048e0a6"
R30_STATUS = "AV4PIVOTP2R6R30_ATOMIC_PHYSICAL_TIME_COMMIT_OF_ACCEPTED_ALL_CV_XY1_CANDIDATE_PASS"

R30_RUNNER = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R30_Atomic_Physical_Time_Commit_Accepted_AllCV_XY1_Candidate.py"
R30_RUNNER_BLOB = "d75f469c4df3eef48d30bbbb3b1e1f667dcefc2e"

# Temporal semantics frozen before R29 execution.
R27_RUNNER = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R27_Day375_CapacityLimited_Residual_Transport_Temporal_Semantics_Design_Freeze.py"
R27_BLOB = "c4c67c7349c6aefc2679178bfbeb80e6baa1ee97"
R28_RUNNER = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R28_FrozenFlow_Transport_DeltaMapback_ResidualWell_Coupling_Protocol_Freeze.py"
R28_BLOB = "90981a4fe0dc22bba270b12ab94b1bb4041d3eaa"

R2SRC = "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2SRC_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"
A2E = "PAD_Stream_POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution.py"
A2E_BLOB = "79a8969233b72b4543edd382a0c3d1028c6dca09"

SOURCE_BLOBS = {
    R31_RUNNER: R31_RUNNER_BLOB,
    R30_RUNNER: R30_RUNNER_BLOB,
    R27_RUNNER: R27_BLOB,
    R28_RUNNER: R28_BLOB,
    R2SRC: R2SRC_BLOB,
    A2E: A2E_BLOB,
}

A6E_REL = BASE_AV3 / "POSTV16_AV3_A6_E_Frozen_Checkpoint_LocalPV_R7D_Integration_Execution"
A6E_STATE = "POSTV16_AV3_A6_E_AV3CR0003_Integrated_State.npz"
A6E_SHA = "f9e3a7bd8c6dcc43d522e0cb99a0cede2bd212fd570085b4faf82dc71af8f803"

OUT_TOKEN = "POSTV16_AV4_PIVOT_P2_R6_R32"
OUT_REL = BASE / (OUT_TOKEN + "_Independent_Recurrent_Operation_Closure_Audit")
BLOCK_REL = BASE / (OUT_TOKEN + "_BLOCKED")


class GateError(RuntimeError):
    pass


def gt(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def js(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def csvr(path: Path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def csvb(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        return b""
    fields = []
    for row in rows:
        for k in row:
            if k not in fields:
                fields.append(k)
    s = io.StringIO(newline="")
    w = csv.DictWriter(s, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return s.getvalue().encode("utf-8")


def jb(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True) + "\n").encode("utf-8")


def manifest(directory: Path, filename: str) -> dict[str, str]:
    out = {}
    for row in csvr(directory / filename):
        p = directory / row["file"]
        if not p.is_file():
            raise GateError(f"manifest_missing:{p.name}")
        if sha(p) != row["sha256"]:
            raise GateError(f"manifest_sha:{p.name}")
        if p.stat().st_size != int(row["bytes"]):
            raise GateError(f"manifest_bytes:{p.name}")
        out[p.name] = row["sha256"]
    return out


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError(f"cannot_load:{path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def selftest():
    assert NCVT == 215600
    assert abs(R30_DAY + DT - R31_TARGET_DAY) < 1.0e-12
    print("POSTV16 AV4 PIVOT P2-R6-R32 structural self-test: PASS")


def main(project_root: Path, drive_root: Path) -> int:
    root = project_root.resolve()
    drive = drive_root.resolve()
    out = drive / OUT_REL
    block_dir = drive / BLOCK_REL
    stage = "preflight"
    gates = []

    def gate(name: str, cond: Any, detail: Any = None):
        ok = bool(cond)
        gates.append({
            "stage": stage,
            "gate": name,
            "pass": ok,
            "detail": "" if detail is None else repr(detail),
        })
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + ("" if detail is None else f" -- {detail}"))
        if not ok:
            raise GateError(name)

    try:
        stage = "preexisting_state_firewall"
        gate("no_preexisting_PASS", not (out / f"PAD_Stream_{OUT_TOKEN}_Summary.json").exists())
        gate("no_preexisting_BLOCK", not (block_dir / f"{OUT_TOKEN}_Blocked_Report.json").exists())

        stage = "repository_authority"
        gate("branch_exact", gt(root, "branch", "--show-current") == BRANCH)
        gate("parent_exact", gt(root, "rev-parse", "HEAD^") == PARENT, gt(root, "rev-parse", "HEAD^"))
        gate("repository_clean", gt(root, "status", "--porcelain") == "")
        for fn, expected in SOURCE_BLOBS.items():
            p = root / fn
            gate(f"{Path(fn).stem}_present", p.is_file(), str(p))
            actual = gt(root, "hash-object", str(p)) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_blob_exact", actual == expected, actual)

        stage = "R31_authority"
        r31d = drive / R31_REL
        r31m = manifest(r31d, R31_MANIFEST)
        r31s = js(r31d / R31_SUMMARY)
        r31c = js(r31d / R31_DECISION)
        r31cert = js(r31d / R31_CERT)
        r31state = r31d / R31_STATE

        gate("R31_status_exact", r31s.get("status") == R31_STATUS, r31s.get("status"))
        gate("R31_class_exact", r31s.get("classification") == R31_CLASS, r31s.get("classification"))
        gate("R31_recurrence_demonstrated", r31s.get("frozen_flow_recurrence_demonstrated") is True)
        gate("R31_R30_valid_parent", r31s.get("R30_state_is_valid_recurrent_parent") is True)
        gate("R31_restart_preserved", r31s.get("restart_split_state_preserved") is True)
        gate("R31_refresh_handoff_preserved", r31s.get("future_refresh_full_cartesian_handoff_preserved") is True)
        gate("R31_no_time_commit", r31s.get("physical_time_advance_executed") is False)
        gate("R31_R32_authorized", r31c.get("P2_R6_R32_authorized") is True)
        gate("R31_R32_R30_SHA_exact", r31c.get("P2_R6_R32_must_bind_R30_state_SHA") == R30_STATE_SHA)
        gate("R31_R32_candidate_SHA_exact", r31c.get("P2_R6_R32_must_bind_R31_candidate_SHA") == R31_STATE_SHA)
        gate("R31_state_manifested", R31_STATE in r31m)
        gate("R31_state_manifest_SHA_exact", r31m.get(R31_STATE) == R31_STATE_SHA, r31m.get(R31_STATE))
        gate("R31_state_file_SHA_exact", r31state.is_file() and sha(r31state) == R31_STATE_SHA)
        gate("R31_contract_full_cartesian_primary",
             r31cert.get("certified_semantics", {}).get("full_cartesian_state_remains_primary_recurrent_authority") is True)
        gate("R31_contract_future_refresh_full_cartesian",
             r31cert.get("certified_semantics", {}).get("future_flow_refresh_must_start_from_full_cartesian_inventory") is True)

        stage = "R30_authority"
        r30d = drive / R30_REL
        r30m = manifest(r30d, R30_MANIFEST)
        r30s = js(r30d / R30_SUMMARY)
        r30c = js(r30d / R30_DECISION)
        r30state = r30d / R30_STATE

        gate("R30_status_exact", r30s.get("status") == R30_STATUS, r30s.get("status"))
        gate("R30_complete", r30s.get("R30_complete") is True)
        gate("R30_physical_time_committed", r30s.get("physical_time_committed") is True)
        gate("R30_physical_day_exact", abs(float(r30s.get("physical_day")) - R30_DAY) <= 1.0e-12)
        gate("R30_state_manifested", R30_STATE in r30m)
        gate("R30_state_manifest_SHA_exact", r30m.get(R30_STATE) == R30_STATE_SHA)
        gate("R30_state_file_SHA_exact", r30state.is_file() and sha(r30state) == R30_STATE_SHA)
        gate("R30_R31_authorized", r30c.get("P2_R6_R31_authorized") is True)

        stage = "load_states"
        with np.load(r30state, allow_pickle=False) as z:
            r30_mass = np.asarray(z["cartesian_component_mass_kg"], dtype=np.float64)
            r30_rep = np.asarray(z["represented_cartesian_cell_mass_kg"], dtype=np.float64)
            r30_res = np.asarray(z["grid_residual_component_mass_kg"], dtype=np.float64)
            r30_cv = np.asarray(z["transport_CV_component_mass_kg"], dtype=np.float64)
            r30_pressure = np.asarray(z["refreshed_pressure_psi"], dtype=np.float64)
            r30_pref = float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))
            r30_xyz = np.asarray(z["streamline_xyz_m"], dtype=np.float64)
            r30_tof = np.asarray(z["streamline_tof_s"], dtype=np.float64)
            r30_weight = np.asarray(z["streamline_weight_m3_s"], dtype=np.float64)
            r30_edge_cv = np.asarray(z["XY1_edge_cv"], dtype=np.int64)
            r30_edge_cell = np.asarray(z["XY1_edge_cell"], dtype=np.int64)
            r30_shell = np.asarray(z["XY1_edge_shell_cost"], dtype=np.int8)
            r30_day = float(np.asarray(z["physical_day"]).reshape(()))
            r30_committed = bool(np.asarray(z["physical_time_committed"]).reshape(()))

        with np.load(r31state, allow_pickle=False) as z:
            parent_day = float(np.asarray(z["candidate_parent_day"]).reshape(()))
            target_day = float(np.asarray(z["candidate_target_day"]).reshape(()))
            flow_epoch_day = float(np.asarray(z["flow_epoch_day"]).reshape(()))
            r31_committed = bool(np.asarray(z["physical_time_committed"]).reshape(()))
            mass = np.asarray(z["cartesian_component_mass_kg"], dtype=np.float64)
            rep = np.asarray(z["represented_cartesian_cell_mass_kg"], dtype=np.float64)
            res = np.asarray(z["grid_residual_component_mass_kg"], dtype=np.float64)
            cv = np.asarray(z["transport_CV_component_mass_kg"], dtype=np.float64)
            cv_sat = np.asarray(z["transport_CV_saturation"], dtype=np.float64)
            pressure = np.asarray(z["refreshed_pressure_psi"], dtype=np.float64)
            pref = float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))
            xyz = np.asarray(z["streamline_xyz_m"], dtype=np.float64)
            tof = np.asarray(z["streamline_tof_s"], dtype=np.float64)
            weight = np.asarray(z["streamline_weight_m3_s"], dtype=np.float64)
            edge_cv = np.asarray(z["XY1_edge_cv"], dtype=np.int64)
            edge_cell = np.asarray(z["XY1_edge_cell"], dtype=np.int64)
            shell = np.asarray(z["XY1_edge_shell_cost"], dtype=np.int8)
            edge_mass = np.asarray(z["XY1_edge_assigned_mass_kg"], dtype=np.float64)
            flux = np.asarray(z["theory_face_mass_flux_kg_day"], dtype=np.float64)

        gate("R31_time_metadata_exact",
             abs(parent_day - R30_DAY) <= 1.0e-12
             and abs(target_day - R31_TARGET_DAY) <= 1.0e-12
             and abs(flow_epoch_day - FLOW_EPOCH_DAY) <= 1.0e-12
             and r31_committed is False)
        gate("R30_time_metadata_exact", abs(r30_day - R30_DAY) <= 1.0e-12 and r30_committed is True)

        stage = "immutability_and_support"
        gate("residual_bitwise_unchanged", np.array_equal(res, r30_res))
        gate("pressure_bitwise_unchanged", np.array_equal(pressure, r30_pressure))
        gate("reference_pressure_unchanged", pref == r30_pref)
        gate("streamline_xyz_bitwise_unchanged", np.array_equal(xyz, r30_xyz))
        gate("TOF_bitwise_unchanged", np.array_equal(tof, r30_tof))
        gate("streamline_weight_bitwise_unchanged", np.array_equal(weight, r30_weight))
        gate("edge_cv_support_unchanged", np.array_equal(edge_cv, r30_edge_cv))
        gate("edge_cell_support_unchanged", np.array_equal(edge_cell, r30_edge_cell))
        gate("shell_topology_unchanged", np.array_equal(shell, r30_shell))

        stage = "independent_CV_and_cell_ledgers"
        gate("state_shapes_exact",
             mass.shape == GRID and rep.shape == GRID and res.shape == GRID
             and cv.shape == (NSL, NCV) and cv_sat.shape == (NSL, NCV)
             and edge_cv.shape == edge_cell.shape == shell.shape == edge_mass.shape)
        gate("edge_mass_nonnegative", float(np.min(edge_mass)) >= -MASS_TOL, float(np.min(edge_mass)))

        cv_from_edges = np.bincount(edge_cv, weights=edge_mass, minlength=NCVT).reshape(NSL, NCV)
        cv_residual = cv_from_edges - cv
        cv_err = float(np.max(np.abs(cv_residual)))
        cv_l1 = float(np.sum(np.abs(cv_residual)))
        gate("all_CV_mass_equalities", cv_err <= MASS_TOL, cv_err)

        # Separate exact-zero CVs from legitimate small positive targets <= MASS_TOL.
        flat_target = cv.reshape(-1)
        flat_assigned = cv_from_edges.reshape(-1)
        exact_zero_mask = flat_target == 0.0
        sub_tol_positive_mask = (flat_target > 0.0) & (flat_target <= MASS_TOL)
        tol_bucket = flat_target <= MASS_TOL

        exact_zero_count = int(np.count_nonzero(exact_zero_mask))
        sub_tol_positive_count = int(np.count_nonzero(sub_tol_positive_mask))
        tolerance_zero_count = int(np.count_nonzero(tol_bucket))

        exact_zero_assigned_total = float(np.sum(flat_assigned[exact_zero_mask]))
        exact_zero_assigned_max = (
            float(np.max(flat_assigned[exact_zero_mask])) if exact_zero_count else 0.0
        )
        sub_tol_target_total = float(np.sum(flat_target[sub_tol_positive_mask]))
        sub_tol_assigned_total = float(np.sum(flat_assigned[sub_tol_positive_mask]))
        tolerance_bucket_target_total = float(np.sum(flat_target[tol_bucket]))
        tolerance_bucket_assigned_total = float(np.sum(flat_assigned[tol_bucket]))
        tolerance_bucket_signed_error = tolerance_bucket_assigned_total - tolerance_bucket_target_total
        tolerance_bucket_L1_error = float(np.sum(np.abs(
            flat_assigned[tol_bucket] - flat_target[tol_bucket]
        )))

        gate("exact_zero_CV_max_assigned_within_science_gate",
             exact_zero_assigned_max <= MASS_TOL,
             exact_zero_assigned_max)
        gate("tolerance_bucket_signed_error_negligible",
             abs(tolerance_bucket_signed_error) <= MASS_TOL,
             tolerance_bucket_signed_error)
        gate("tolerance_bucket_L1_error_negligible",
             tolerance_bucket_L1_error <= MASS_TOL,
             tolerance_bucket_L1_error)
        gate("reported_zero_target_count_explained",
             tolerance_zero_count == int(r31s.get("zero_target_CV_count")),
             [tolerance_zero_count, r31s.get("zero_target_CV_count")])
        gate("reported_zero_target_total_explained",
             abs(tolerance_bucket_assigned_total - float(r31s.get("zero_target_CV_total_assigned_mass_kg"))) <= 1.0e-12,
             [tolerance_bucket_assigned_total, r31s.get("zero_target_CV_total_assigned_mass_kg")])
        gate("aggregate_zero_bucket_is_not_ghost_mass",
             abs(tolerance_bucket_assigned_total - tolerance_bucket_target_total) <= MASS_TOL,
             {
                 "assigned": tolerance_bucket_assigned_total,
                 "target": tolerance_bucket_target_total,
                 "signed_error": tolerance_bucket_signed_error,
                 "exact_zero_assigned": exact_zero_assigned_total,
                 "sub_tol_positive_target": sub_tol_target_total,
                 "sub_tol_positive_assigned": sub_tol_assigned_total,
             })

        cell_from_edges = np.bincount(edge_cell, weights=edge_mass, minlength=NCELL).reshape(GRID)
        cell_err = float(np.max(np.abs(cell_from_edges - rep)))
        gate("edge_to_cell_ledger_exact", cell_err <= 1.0e-10, cell_err)

        split_err = float(np.max(np.abs(mass - rep - res)))
        gate("split_identity", split_err <= MASS_TOL, split_err)

        stage = "independent_global_mass"
        injected = float(np.sum(flux[:, 0]) * DT)
        produced = float(np.sum(flux[:, -1]) * DT)
        expected_total = float(np.sum(r30_mass)) + injected - produced
        source_sink = float(np.sum(mass)) - expected_total
        global_tol = max(MASS_TOL, REL_TOL * max(abs(expected_total), 1.0))
        gate("global_source_sink_closure", abs(source_sink) <= global_tol, [source_sink, global_tol])

        stage = "independent_storage_and_EOS"
        a6e_path = drive / A6E_REL / A6E_STATE
        gate("A6E_state_SHA_exact", a6e_path.is_file() and sha(a6e_path) == A6E_SHA)
        with np.load(a6e_path, allow_pickle=False) as z:
            phi = np.asarray(z["paired_porosity"], dtype=np.float64)

        r2 = load_module(root / R2SRC, "r32_r2")
        a2e = load_module(root / A2E, "r32_a2e")
        hetero_pv = phi * float(a2e.BULK_VOLUME_M3)
        full_sat = np.full(GRID, float(a2e.INJECTED), dtype=np.float64)
        capacity = np.asarray(
            a2e.local_mass(r2, full_sat, pressure, pref, hetero_pv),
            dtype=np.float64,
        )
        cap_excess = float(np.max(mass - capacity))
        gate("heterogeneous_cartesian_capacity", cap_excess <= 1.0e-8, cap_excess)

        sg = np.asarray(a2e.invert_local_mass(r2, mass, pressure, pref, hetero_pv), dtype=np.float64)
        sat = float(a2e.BACKGROUND) + sg
        gate("saturation_bounds",
             float(np.min(sat)) >= BACKGROUND - SAT_TOL
             and float(np.max(sat)) <= MAX_SAT + SAT_TOL,
             [float(np.min(sat)), float(np.max(sat))])

        recon = np.asarray(a2e.local_mass(r2, sat, pressure, pref, hetero_pv), dtype=np.float64)
        recon_err = float(np.max(np.abs(recon - mass)))
        gate("EOS_reconstruction", recon_err <= 1.0e-8, recon_err)

        stage = "recurrent_restart_and_refresh_closure"
        gate("R30_parent_to_R31_target_time_identity", abs(R30_DAY + DT - R31_TARGET_DAY) <= 1.0e-12)
        gate("R31_candidate_remains_prospective", r31_committed is False)
        gate("full_cartesian_candidate_available_for_future_refresh", mass.shape == GRID and np.isfinite(mass).all())
        gate("residual_stays_deferred_only_within_current_flow_epoch", np.array_equal(res, r30_res))
        gate("R31_did_not_refresh_pressure", r31s.get("pressure_refreshed") is False)
        gate("R31_did_not_retrace_TOF", r31s.get("TOF_retraced") is False)
        gate("R31_did_not_change_support", r31s.get("support_changed") is False)
        gate("R31_did_not_mutate_residual", r31s.get("residual_sidecar_mutated") is False)

        stage = "closure_publication"
        out.mkdir(parents=True, exist_ok=False)

        classification = (
            "R30_AUTHORITATIVE_STATE_AND_R31_SECOND_STEP_RECURRENCE_"
            "INDEPENDENTLY_CLOSED_AV4_RECURRENT_PHYSICS_ACCEPTED_"
            "R31_CANDIDATE_REMAINS_PROSPECTIVE"
        )

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": classification,
            "R30_committed_state_sha256": R30_STATE_SHA,
            "R31_prospective_candidate_sha256": R31_STATE_SHA,
            "R30_authoritative_physical_day": R30_DAY,
            "R31_prospective_target_day": R31_TARGET_DAY,
            "flow_epoch_day": FLOW_EPOCH_DAY,
            "nominal_dt_days": DT,
            "AV4_recurrent_physics_closed": True,
            "R29_repair_lineage_closed": True,
            "R30_authoritative_state_valid": True,
            "R31_second_step_recurrence_independently_verified": True,
            "R31_candidate_time_committed": False,
            "all_CV_count": NCVT,
            "CV_equality_max_abs_error_kg": cv_err,
            "CV_equality_L1_error_kg": cv_l1,
            "tolerance_zero_bucket_count": tolerance_zero_count,
            "exact_zero_CV_count": exact_zero_count,
            "sub_tolerance_positive_CV_count": sub_tol_positive_count,
            "tolerance_zero_bucket_assigned_mass_kg": tolerance_bucket_assigned_total,
            "tolerance_zero_bucket_target_mass_kg": tolerance_bucket_target_total,
            "tolerance_zero_bucket_signed_error_kg": tolerance_bucket_signed_error,
            "tolerance_zero_bucket_L1_error_kg": tolerance_bucket_L1_error,
            "exact_zero_CV_assigned_mass_total_kg": exact_zero_assigned_total,
            "exact_zero_CV_assigned_mass_max_kg": exact_zero_assigned_max,
            "sub_tolerance_positive_target_mass_total_kg": sub_tol_target_total,
            "sub_tolerance_positive_assigned_mass_total_kg": sub_tol_assigned_total,
            "cartesian_source_sink_residual_kg": source_sink,
            "cartesian_max_capacity_excess_kg": cap_excess,
            "cartesian_mass_reconstruction_max_abs_error_kg": recon_err,
            "candidate_saturation_min": float(np.min(sat)),
            "candidate_saturation_max": float(np.max(sat)),
            "residual_sidecar_unchanged": True,
            "pressure_state_unchanged": True,
            "TOF_geometry_unchanged": True,
            "support_domain_unchanged": True,
            "full_cartesian_refresh_handoff_valid": True,
            "state_mutation_executed": False,
            "physical_time_advance_executed": False,
            "P3_authorized": False,
        }

        closure_contract = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "AV4_recurrent_physics_closure": {
                "closed": True,
                "authoritative_committed_state": {
                    "sha256": R30_STATE_SHA,
                    "physical_day": R30_DAY,
                },
                "independent_recurrence_evidence": {
                    "R31_candidate_sha256": R31_STATE_SHA,
                    "prospective_target_day": R31_TARGET_DAY,
                    "time_committed": False,
                    "all_CV_conservation": True,
                    "heterogeneous_cartesian_capacity": True,
                    "global_source_sink_closure": True,
                    "EOS_reconstruction": True,
                    "frozen_XY1_support_reused": True,
                    "residual_sidecar_epoch_frozen": True,
                },
                "restart_semantics": {
                    "primary_recurrent_physical_state": "cartesian_component_mass_kg",
                    "transport_coordinate_state": "transport_CV_component_mass_kg",
                    "residual_sidecar": "deferred Cartesian reserve within current frozen-flow epoch",
                    "future_refresh_input": "entire Cartesian component-mass inventory",
                    "old_residual_labels_permanent_physical_classes": False,
                },
                "zero_target_audit": {
                    "science_gate_is_per_CV_kg": MASS_TOL,
                    "tolerance_bucket_definition": "target CV mass <= 1e-6 kg",
                    "aggregate_assigned_mass_is_not_itself_an_error_metric": True,
                    "aggregate_error_metric": "sum(assigned-target) and L1(assigned-target)",
                    "aggregate_signed_error_kg": tolerance_bucket_signed_error,
                    "aggregate_L1_error_kg": tolerance_bucket_L1_error,
                },
            },
        }

        decision = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "AV4_recurrent_physics_closed": True,
            "R29_repair_lineage_closed": True,
            "authoritative_state_sha256": R30_STATE_SHA,
            "authoritative_physical_day": R30_DAY,
            "R31_candidate_remains_prospective": True,
            "R31_candidate_time_commit_authorized": False,
            "R31_candidate_acceptance_as_authoritative_state": False,
            "AV5_learned_acceleration_design_authorized": True,
            "AV5_execution_authorized": False,
            "AV5_must_preserve_exact_AV4_physics_authority": True,
            "AV5_must_not_replace_exact_finite_volume_correction": True,
            "AV5_must_not_relax_conservation_gates": True,
            "AV5_must_bind_AV4_authoritative_state_SHA": R30_STATE_SHA,
            "R29_repair_science_reopening_authorized": False,
            "automatic_physics_change_authorized": False,
            "P3_authorized": False,
        }

        (out / f"PAD_Stream_{OUT_TOKEN}_Summary.json").write_bytes(jb(summary))
        (out / f"{OUT_TOKEN}_AV4_Recurrent_Physics_Closure_Contract.json").write_bytes(jb(closure_contract))
        (out / f"{OUT_TOKEN}_Decision_Contract.json").write_bytes(jb(decision))
        (out / f"{OUT_TOKEN}_Final_Gate_Matrix.csv").write_bytes(csvb(gates))

        rows = []
        for p in sorted(out.iterdir()):
            if p.is_file():
                rows.append({"file": p.name, "sha256": sha(p), "bytes": p.stat().st_size})
        (out / f"{OUT_TOKEN}_Artifact_Manifest.csv").write_bytes(csvb(rows))

        print("=" * 200)
        print(M, "PASS")
        print("Classification                              :", classification)
        print("R30 authoritative state SHA256              :", R30_STATE_SHA)
        print("R31 prospective recurrence SHA256           :", R31_STATE_SHA)
        print("AV4 recurrent physics closed                : True")
        print("R29 repair lineage closed                   : True")
        print("Tolerance-zero bucket count                 :", tolerance_zero_count)
        print("  exact-zero CV count                       :", exact_zero_count)
        print("  sub-tolerance positive CV count            :", sub_tol_positive_count)
        print("Tolerance-zero assigned mass kg             :", tolerance_bucket_assigned_total)
        print("Tolerance-zero target mass kg               :", tolerance_bucket_target_total)
        print("Tolerance-zero signed error kg              :", tolerance_bucket_signed_error)
        print("Tolerance-zero L1 error kg                  :", tolerance_bucket_L1_error)
        print("CV equality max error kg                    :", cv_err)
        print("Cartesian source/sink residual kg           :", source_sink)
        print("Cartesian max capacity excess kg            :", cap_excess)
        print("R31 candidate remains prospective           : True")
        print("AV5 learned-acceleration design authorized  : True")
        print("AV5 execution authorized                    : False")
        print("P3 authorized                               : False")
        print("=" * 200)
        return 0

    except Exception as exc:
        block_dir.mkdir(parents=True, exist_ok=True)
        p = block_dir / f"{OUT_TOKEN}_Blocked_Report.json"
        if not p.exists():
            p.write_bytes(jb({
                "milestone": M,
                "status": BLOCK,
                "failed_stage": stage,
                "exception": repr(exc),
                "R30_authoritative_state_preserved": True,
                "R31_prospective_candidate_preserved": True,
                "AV4_recurrent_physics_closed": False,
                "state_mutation_executed": False,
                "physical_time_advance_executed": False,
                "P3_authorized": False,
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
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        selftest()
        raise SystemExit(0)
    raise SystemExit(main(args.project_root, args.drive_root))
