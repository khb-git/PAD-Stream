#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, hashlib, importlib.util, io, json, subprocess, sys, zipfile
from pathlib import Path
from typing import Any
import numpy as np

M = "POSTV16-AV4-PIVOT-P2-R6-R29"
NAME = "Controlled Post-Day375 Frozen-Flow Capacity-Limited Split-State Transport Candidate Execution — No Time Commit"

PASS = (
    "AV4PIVOTP2R6R29_CONTROLLED_POSTDAY375_FROZEN_FLOW_CAPACITY_LIMITED_"
    "SPLIT_STATE_TRANSPORT_CANDIDATE_EXECUTION_PASS_NO_TIME_COMMIT"
)
SCI_FAIL = (
    "AV4PIVOTP2R6R29_CONTROLLED_POSTDAY375_FROZEN_FLOW_CAPACITY_LIMITED_"
    "SPLIT_STATE_TRANSPORT_CANDIDATE_SCIENTIFIC_FAIL_NO_AUTOMATIC_RERUN"
)
BLOCK = "AV4PIVOTP2R6R29_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "9d23ca09132d561b0ef93b5e6eab89f49232f805"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

GRID = (15, 50, 50)
NSL = 1078
NN = 201
NCV = 200
DAY = 375.0
DAY_TO_S = 86400.0
FT_TO_M = 0.3048
BACKGROUND_SATURATION = 0.20
MAX_SATURATION = 0.80
MAX_INCREMENTAL_CO2_SATURATION = 0.60
INJECTOR_MASS_RATE_KG_DAY = 500000.0

DT_DAYS = 0.03721673128859954
CANDIDATE_TARGET_DAY = 375.0372167312886

MASS_TOL = 1e-6
CAPACITY_TOL = 1e-7
SAT_TOL = 1e-10
SOURCE_SINK_REL_TOL = 1e-10

CELL_PORE_VOLUME_M3 = (
    0.20
    * (20.0 * FT_TO_M)
    * (20.0 * FT_TO_M)
    * (4.0 * FT_TO_M)
)

R28_REL = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R28_"
    "FrozenFlow_Transport_DeltaMapback_ResidualWell_Coupling_Protocol_Freeze"
)
R28_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R28_Summary.json"
R28_PROTOCOL = "POSTV16_AV4_PIVOT_P2_R6_R28_FrozenFlow_Transport_DeltaMapback_Protocol.json"
R28_DECISION = "POSTV16_AV4_PIVOT_P2_R6_R28_Decision_Contract.json"
R28_WELL_AUDIT = "POSTV16_AV4_PIVOT_P2_R6_R28_Residual_Well_Overlap_Audit.csv"
R28_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R28_Artifact_Manifest.csv"
R28_STATUS = (
    "AV4PIVOTP2R6R28_FROZEN_FLOW_TRANSPORT_DELTA_MAPBACK_"
    "RESIDUAL_WELL_COUPLING_PROTOCOL_FREEZE_PASS_NO_EXECUTION"
)
R28_CLASSIFICATION = (
    "R6R28_FROZEN_FLOW_CV_COMPONENT_MASS_DELTA_MAPBACK_AND_DEFERRED_RESIDUAL_"
    "WELL_COUPLING_PROTOCOL_FROZEN_R29_PROVISIONAL_TRANSPORT_CANDIDATE_EXECUTION_NEXT"
)

R26_REL = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R26_"
    "Day375_CapacityLimited_SplitState_Restart_Representation_Closure_and_Acceptance_Audit"
)
R26_ACCEPTANCE = "POSTV16_AV4_PIVOT_P2_R6_R26_Day375_SplitState_Acceptance_Contract.json"
R26_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R26_Artifact_Manifest.csv"

R25R3_REL = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R25_R3_"
    "Controlled_Day375_CapacityLimited_ExactSupport_SplitState_"
    "Reprojection_Execution_Stage2_PresolveOff"
)
R25R3_STATE = "POSTV16_AV4_PIVOT_P2_R6_R25_R3_CapacityLimited_SplitState_Day375.npz"
R25R3_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R25_R3_Artifact_Manifest.csv"
R25R3_STATE_SHA256 = "9893e2476bce1d46213cdd1304e60ad93b49ea285e084d06743a2ffab25f721f"

R22_EPOCH_SHA256 = "7f030fd3676eb3b61bc7f341dff8cb82659e87e210640a9488bf6fb15e7bd80e"
PRESSURE_EPOCH_SHA256 = "99d73cab1d33191a68578f29d3c03f9fac07ed77c39e124cc8eb5e5bf75aa84d"

R28_RUNNER = (
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R28_"
    "FrozenFlow_Transport_DeltaMapback_ResidualWell_Coupling_Protocol_Freeze.py"
)
R28_BLOB = "90981a4fe0dc22bba270b12ab94b1bb4041d3eaa"

R25R3_RUNNER = (
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R25_R3_"
    "Controlled_CapacityLimited_Reprojection_Stage2_PresolveOff.py"
)
R25R3_BLOB = "65cab626419137b191f2c53a4c543d9805ccf68d"

E37A = "PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB = "0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"
R2 = "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"
SG7D = "PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"
SG7D_BLOB = "890088c0c0fcab415a2c7351c5079ca8ee12bf82"
SG7A = "PAD_Stream_V15SG7A_Full_Physics_TOF_Transport.py"
SG7A_BLOB = "a4dd47338e7a85f130a6a70d0a41211e38c655f8"
E36 = "PAD_Stream_V16E36_Short_Adaptive_SGSim_Rollout_and_Early_Plume_Snapshot_Validation.py"
E36_BLOB = "9ab4035c95a25bd61c649f86c82d88f059cef9e2"

SOURCE_BLOBS = {
    R28_RUNNER: R28_BLOB,
    R25R3_RUNNER: R25R3_BLOB,
    E37A: E37A_BLOB,
    R2: R2_BLOB,
    SG7D: SG7D_BLOB,
    SG7A: SG7A_BLOB,
    E36: E36_BLOB,
}

OUT_TOKEN = "POSTV16_AV4_PIVOT_P2_R6_R29"
OUT_REL = BASE / (OUT_TOKEN + "_Controlled_FrozenFlow_Transport_Candidate_Execution_NoTimeCommit")
FAIL_REL = BASE / (OUT_TOKEN + "_SCIENTIFIC_FAIL")
BLOCK_REL = BASE / (OUT_TOKEN + "_BLOCKED")


class GateError(RuntimeError):
    pass


class ScientificFail(RuntimeError):
    def __init__(self, gate: str, detail: Any):
        super().__init__(f"{gate}:{detail}")
        self.gate = gate
        self.detail = detail


def gt(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def js(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def csvr(path: Path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def csvb(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        return b""
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    s = io.StringIO(newline="")
    w = csv.DictWriter(s, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return s.getvalue().encode("utf-8")


def jb(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True) + "\n").encode("utf-8")


def manifest(directory: Path, filename: str) -> dict[str, str]:
    rows = csvr(directory / filename)
    out: dict[str, str] = {}
    for row in rows:
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
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def deterministic_npz_bytes(arrays: dict[str, Any]) -> bytes:
    outer = io.BytesIO()
    with zipfile.ZipFile(outer, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for key in sorted(arrays):
            arr = np.asarray(arrays[key])
            if arr.dtype == object:
                raise GateError(f"object_dtype_forbidden:{key}")
            payload = io.BytesIO()
            np.lib.format.write_array(payload, arr, allow_pickle=False)
            info = zipfile.ZipInfo(f"{key}.npy")
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            zf.writestr(info, payload.getvalue())
    return outer.getvalue()


def selftest() -> None:
    assert CANDIDATE_TARGET_DAY > DAY
    assert abs((CANDIDATE_TARGET_DAY - DAY) - DT_DAYS) < 1e-12
    parent = np.asarray([10.0, 20.0])
    represented = np.asarray([4.0, 9.0])
    residual = parent - represented
    delta = np.asarray([1.0, -2.0])
    rep_candidate = represented + delta
    candidate = residual + rep_candidate
    assert np.allclose(candidate, parent + delta)
    assert np.all(rep_candidate >= 0.0)
    print("POSTV16 AV4 PIVOT P2-R6-R29 structural self-test: PASS")


def main(project_root: Path, drive_root: Path) -> int:
    root = project_root.resolve()
    drive = drive_root.resolve()
    out = drive / OUT_REL
    fail_dir = drive / FAIL_REL
    block_dir = drive / BLOCK_REL
    stage = "preflight"
    gates: list[dict[str, Any]] = []
    science_started = False

    def gate(name: str, cond: Any, detail: Any = None) -> None:
        ok = bool(cond)
        gates.append({"stage": stage, "gate": name, "pass": ok, "detail": "" if detail is None else repr(detail)})
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + ("" if detail is None else f" -- {detail}"))
        if not ok:
            raise GateError(name)

    def sci_gate(name: str, cond: Any, detail: Any = None) -> None:
        ok = bool(cond)
        gates.append({"stage": stage, "gate": name, "pass": ok, "detail": "" if detail is None else repr(detail)})
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + ("" if detail is None else f" -- {detail}"))
        if not ok:
            raise ScientificFail(name, detail)

    try:
        stage = "preexisting_state_firewall"
        gate("no_preexisting_R29_PASS", not (out / f"PAD_Stream_{OUT_TOKEN}_Summary.json").exists())
        gate("no_preexisting_R29_FAIL", not (fail_dir / f"{OUT_TOKEN}_Scientific_Fail_Report.json").exists())
        gate("no_preexisting_R29_BLOCK", not (block_dir / f"{OUT_TOKEN}_Blocked_Report.json").exists())

        stage = "repository_authority"
        gate("branch_exact", gt(root, "branch", "--show-current") == BRANCH)
        gate("parent_is_R28_commit", gt(root, "rev-parse", "HEAD^") == PARENT)
        gate("repository_clean", gt(root, "status", "--porcelain") == "")
        for filename, expected in SOURCE_BLOBS.items():
            p = root / filename
            gate(f"{Path(filename).stem}_present", p.is_file(), str(p))
            actual = gt(root, "hash-object", str(p)) if p.is_file() else "missing"
            gate(f"{Path(filename).stem}_blob_exact", actual == expected, actual)

        stage = "R28_protocol_authority"
        r28 = drive / R28_REL
        manifest(r28, R28_MANIFEST)
        s28 = js(r28 / R28_SUMMARY)
        p28 = js(r28 / R28_PROTOCOL)
        d28 = js(r28 / R28_DECISION)
        well_rows = csvr(r28 / R28_WELL_AUDIT)

        gate("R28_status_exact", s28.get("status") == R28_STATUS, s28.get("status"))
        gate("R28_classification_exact", s28.get("classification") == R28_CLASSIFICATION, s28.get("classification"))
        gate("R28_state_SHA_exact", s28.get("accepted_state_sha256") == R25R3_STATE_SHA256)
        gate("R28_well_completion_count_exact", len(well_rows) == 25, len(well_rows))
        gate("R28_dt_exact", float(s28["nominal_dt_days"]) == DT_DAYS, s28["nominal_dt_days"])
        gate("R28_target_day_exact", float(s28["candidate_target_day"]) == CANDIDATE_TARGET_DAY)
        gate("R28_delta_mapback_required", s28.get("delta_mapback_required") is True)
        gate("R28_absolute_mapback_forbidden", s28.get("absolute_mapback_forbidden") is True)
        gate("R28_physical_time_commit_locked", s28.get("physical_time_commit_authorized_now") is False)

        gate("R29_authorized", d28.get("P2_R6_R29_authorized") is True)
        gate("R29_execution_authorized", d28.get("P2_R6_R29_execution_authorized") is True)
        gate("R29_candidate_only", d28.get("P2_R6_R29_candidate_only") is True)
        gate("R29_state_SHA_bound", d28.get("P2_R6_R29_R25R3_state_sha256") == R25R3_STATE_SHA256)
        gate("R29_dt_bound", float(d28["P2_R6_R29_dt_days"]) == DT_DAYS)
        gate("R29_target_day_bound", float(d28["P2_R6_R29_candidate_target_day"]) == CANDIDATE_TARGET_DAY)
        gate("residual_direct_well_exchange_forbidden", d28.get("residual_direct_well_exchange_authorized") is False)
        gate("CV_boundary_well_flux_only", d28.get("CV_boundary_well_flux_is_only_external_exchange") is True)
        gate("CV_delta_mapback_authorized", d28.get("CV_delta_mapback_authorized") is True)
        gate("residual_sidecar_mutation_forbidden", d28.get("residual_sidecar_mutation_authorized") is False)
        gate("automatic_dt_reduction_forbidden", d28.get("automatic_dt_reduction_authorized") is False)
        gate("support_growth_forbidden", d28.get("support_growth_authorized") is False)
        gate("time_commit_forbidden", d28.get("physical_time_advance_authorized") is False)
        gate("pressure_refresh_forbidden", d28.get("pressure_refresh_authorized") is False)

        residual_rule = p28.get("residual_preservation", {})
        gate("R28_residual_frozen_exact", residual_rule.get("residual_grid_block_is_unchanged_during_R29_candidate") is True)
        gate("R28_represented_nonnegative_required", residual_rule.get("represented_grid_candidate_nonnegative_required") is True)
        gate("R28_delta_may_not_consume_residual", residual_rule.get("delta_may_not_consume_frozen_residual") is True)

        stage = "accepted_parent_authority"
        r26 = drive / R26_REL
        manifest(r26, R26_MANIFEST)
        a26 = js(r26 / R26_ACCEPTANCE)
        gate("R26_accepts_exact_parent_SHA", a26.get("accepted_state_sha256") == R25R3_STATE_SHA256)
        gate("R26_state_not_rewritten", a26.get("state_rewritten_by_R26") is False)

        r25 = drive / R25R3_REL
        m25 = manifest(r25, R25R3_MANIFEST)
        state_path = r25 / R25R3_STATE
        gate("R25R3_manifest_state_SHA_exact", m25.get(R25R3_STATE) == R25R3_STATE_SHA256)
        gate("R25R3_state_file_SHA_exact", sha(state_path) == R25R3_STATE_SHA256)

        with np.load(state_path, allow_pickle=False) as z:
            grid_parent = np.asarray(z["cartesian_component_mass_kg"], dtype=np.float64)
            represented_parent = np.asarray(z["represented_cartesian_cell_mass_kg"], dtype=np.float64)
            residual_parent = np.asarray(z["grid_residual_component_mass_kg"], dtype=np.float64)
            old_cv_mass = np.asarray(z["transport_CV_component_mass_kg"], dtype=np.float64)
            old_cv_sat = np.asarray(z["transport_CV_saturation"], dtype=np.float64)
            xyz = np.asarray(z["streamline_xyz_m"], dtype=np.float64)
            tof_s = np.asarray(z["streamline_tof_s"], dtype=np.float64)
            weights_m3_s = np.asarray(z["streamline_weight_m3_s"], dtype=np.float64)
            producer_labels = np.asarray(z["producer_labels"]).astype("U32")
            streamline_id = np.asarray(z["streamline_id"], dtype=np.int64)
            pressure_psi = np.asarray(z["refreshed_pressure_psi"], dtype=np.float64)
            p_ref = float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))
            r22_sha = str(np.asarray(z["source_R22_flow_epoch_sha256"]).reshape(()))
            pressure_sha = str(np.asarray(z["source_pressure_epoch_sha256"]).reshape(()))

        gate(
            "parent_shapes_exact",
            grid_parent.shape == GRID
            and represented_parent.shape == GRID
            and residual_parent.shape == GRID
            and old_cv_mass.shape == (NSL, NCV)
            and old_cv_sat.shape == (NSL, NCV)
            and xyz.shape == (NSL, NN, 3)
            and tof_s.shape == (NSL, NN)
            and weights_m3_s.shape == (NSL,)
            and producer_labels.shape == (NSL,),
        )
        gate("parent_R22_SHA_exact", r22_sha == R22_EPOCH_SHA256)
        gate("parent_pressure_SHA_exact", pressure_sha == PRESSURE_EPOCH_SHA256)
        gate("parent_split_identity_exact", float(np.max(np.abs(grid_parent - represented_parent - residual_parent))) <= MASS_TOL)

        parent_total = float(np.sum(grid_parent))
        old_cv_total = float(np.sum(old_cv_mass))
        residual_total = float(np.sum(residual_parent))

        stage = "source_physics_binding"
        e37a = load_module(root / E37A, "r29_e37a")
        r2 = load_module(root / R2, "r29_r2")
        sg7d = load_module(root / SG7D, "r29_sg7d")
        sg7a = load_module(root / SG7A, "r29_sg7a")
        e36 = load_module(root / E36, "r29_e36")

        op = sg7d.build_subsegment_operator(xyz, tof_s / DAY_TO_S, weights_m3_s * DAY_TO_S)
        geometry = e37a.build_control_volume_geometry(r2, op, pressure_psi, p_ref, NSL, NCV)
        face_pressure = e37a.build_face_pressure(e36, sg7d, xyz, pressure_psi)
        gate("face_pressure_shape_exact", face_pressure.shape == (NSL, NCV + 1), face_pressure.shape)

        xi_faces = np.linspace(0.0, 1.0, NCV + 1, dtype=np.float64)
        weights_m3_day = weights_m3_s * DAY_TO_S

        stage = "parent_cartesian_mass_inversion"
        try:
            parent_sg = np.asarray(
                r2._invert_incremental_sg_from_mass(
                    grid_parent,
                    pressure_psi,
                    p_ref,
                    CELL_PORE_VOLUME_M3,
                ),
                dtype=np.float64,
            )
        except Exception as exc:
            raise ScientificFail("parent_cartesian_mass_inversion", repr(exc)) from exc

        parent_sat = BACKGROUND_SATURATION + parent_sg
        parent_reconstructed = float(
            r2.stored_co2_mass_kg(
                parent_sat,
                pressure_psi,
                p_ref,
                CELL_PORE_VOLUME_M3,
            )
        )
        parent_recon_tol = max(MASS_TOL, SOURCE_SINK_REL_TOL * max(abs(parent_total), 1.0))

        science_started = True
        sci_gate(
            "parent_cartesian_mass_reconstruction",
            abs(parent_reconstructed - parent_total) <= parent_recon_tol,
            [parent_reconstructed, parent_total, parent_recon_tol],
        )

        stage = "CV_component_mass_transport"
        try:
            transport = e37a.advance_component_mass_control_volumes(
                r2,
                sg7a,
                old_cv_sat,
                old_cv_mass,
                geometry["cv_pressure_mass_coeff"],
                face_pressure,
                p_ref,
                weights_m3_day,
                xi_faces,
                DT_DAYS,
            )
        except Exception as exc:
            raise ScientificFail("E37A_CV_component_mass_transport", repr(exc)) from exc

        new_cv_mass = np.asarray(transport["new_mass"], dtype=np.float64)
        new_cv_sat = np.asarray(transport["new_saturation"], dtype=np.float64)
        face_mass_flux = np.asarray(transport["face_mass_flux_kg_day"], dtype=np.float64)

        injected = float(transport["injected_mass_kg"])
        produced = float(transport["produced_mass_kg"])
        cv_delta = float(transport["delta_mass_kg"])
        cv_mass_residual = float(transport["mass_residual_kg"])
        expected_injected = INJECTOR_MASS_RATE_KG_DAY * DT_DAYS
        cv_closure_tol = max(MASS_TOL, SOURCE_SINK_REL_TOL * max(abs(injected), abs(cv_delta), 1.0))

        sci_gate("CV_new_mass_shape_exact", new_cv_mass.shape == (NSL, NCV), new_cv_mass.shape)
        sci_gate("CV_new_saturation_shape_exact", new_cv_sat.shape == (NSL, NCV), new_cv_sat.shape)
        sci_gate("CV_mass_nonnegative", float(np.min(new_cv_mass)) >= -MASS_TOL, float(np.min(new_cv_mass)))
        sci_gate(
            "CV_saturation_bounds",
            float(np.min(new_cv_sat)) >= BACKGROUND_SATURATION - SAT_TOL
            and float(np.max(new_cv_sat)) <= MAX_SATURATION + SAT_TOL,
            [float(np.min(new_cv_sat)), float(np.max(new_cv_sat))],
        )
        sci_gate(
            "injected_mass_exact_fixed_rate",
            abs(injected - expected_injected) <= cv_closure_tol,
            [injected, expected_injected, cv_closure_tol],
        )
        sci_gate("produced_mass_nonnegative", produced >= -MASS_TOL, produced)
        sci_gate("CV_global_source_sink_closure", abs(cv_mass_residual) <= cv_closure_tol, [cv_mass_residual, cv_closure_tol])

        producer_rows, aggregate_cut = e37a.producer_rows_from_flux(
            producer_labels,
            weights_m3_day,
            transport["outlet_fractional_flow"],
            face_mass_flux[:, -1],
            DT_DAYS,
        )
        producer_rows_total = float(sum(float(r["CO2_mass_this_step_kg"]) for r in producer_rows))
        sci_gate("producer_rows_all_four_present", len(producer_rows) == 4, [r["producer"] for r in producer_rows])
        sci_gate(
            "producer_rows_mass_matches_transport",
            abs(producer_rows_total - produced) <= cv_closure_tol,
            [producer_rows_total, produced],
        )
        sci_gate("aggregate_producer_CO2_cut_bounded", 0.0 <= aggregate_cut <= 1.0, aggregate_cut)

        stage = "CV_delta_mapback"
        target_final_mass = parent_total + injected - produced

        try:
            mapping = e37a.map_control_volume_increment_to_grid(
                r2,
                parent_sat,
                old_cv_sat,
                new_cv_sat,
                old_cv_mass,
                new_cv_mass,
                geometry,
                pressure_psi,
                p_ref,
                CELL_PORE_VOLUME_M3,
                target_final_mass,
            )
        except Exception as exc:
            raise ScientificFail("E37A_CV_delta_mapback", repr(exc)) from exc

        delta_grid = np.asarray(mapping["deposited_delta_mass"], dtype=np.float64)
        candidate_grid = np.asarray(mapping["corrected_mass"], dtype=np.float64)
        candidate_sat = np.asarray(mapping["corrected_saturation"], dtype=np.float64)
        transfer_residual = float(mapping["transfer_residual_kg"])
        grid_ledger_residual = float(mapping["ledger_residual_kg"])
        grid_inversion_residual = float(mapping["grid_inversion_residual_kg"])

        grid_tol = max(MASS_TOL, SOURCE_SINK_REL_TOL * max(abs(target_final_mass), abs(cv_delta), 1.0))

        sci_gate("delta_grid_shape_exact", delta_grid.shape == GRID, delta_grid.shape)
        sci_gate(
            "CV_to_grid_delta_global_closure",
            abs(float(np.sum(delta_grid)) - cv_delta) <= grid_tol,
            [float(np.sum(delta_grid)), cv_delta, grid_tol],
        )
        sci_gate("subsegment_transfer_residual", abs(transfer_residual) <= grid_tol, [transfer_residual, grid_tol])
        sci_gate("candidate_grid_ledger_closure", abs(grid_ledger_residual) <= grid_tol, [grid_ledger_residual, grid_tol])
        sci_gate("candidate_grid_mass_inversion_closure", abs(grid_inversion_residual) <= grid_tol, [grid_inversion_residual, grid_tol])

        stage = "residual_preservation_and_represented_grid_gate"
        represented_candidate = represented_parent + delta_grid
        min_rep_candidate = float(np.min(represented_candidate))

        sci_gate("represented_grid_candidate_nonnegative", min_rep_candidate >= -MASS_TOL, min_rep_candidate)

        candidate_from_split = residual_parent + represented_candidate
        split_err = float(np.max(np.abs(candidate_from_split - candidate_grid)))
        sci_gate("candidate_split_recomposition_exact", split_err <= MASS_TOL, split_err)

        residual_candidate = residual_parent.copy()
        sci_gate("residual_sidecar_valuewise_unchanged", np.array_equal(residual_candidate, residual_parent))
        sci_gate("delta_does_not_consume_frozen_residual", float(np.min(represented_candidate)) >= -MASS_TOL, float(np.min(represented_candidate)))

        stage = "candidate_cartesian_capacity_and_mass_gates"
        smax = np.full(GRID, MAX_SATURATION, dtype=np.float64)
        rho_max = np.asarray(r2.gas_density_from_state(smax, pressure_psi, p_ref), dtype=np.float64)
        capacity_grid = CELL_PORE_VOLUME_M3 * rho_max * MAX_INCREMENTAL_CO2_SATURATION
        capacity_excess = float(np.max(candidate_grid - capacity_grid))
        min_candidate_mass = float(np.min(candidate_grid))

        sci_gate("candidate_cartesian_mass_nonnegative", min_candidate_mass >= -MASS_TOL, min_candidate_mass)
        sci_gate("candidate_cartesian_cell_pressure_capacity", capacity_excess <= CAPACITY_TOL, capacity_excess)
        sci_gate(
            "candidate_saturation_bounds",
            float(np.min(candidate_sat)) >= BACKGROUND_SATURATION - SAT_TOL
            and float(np.max(candidate_sat)) <= MAX_SATURATION + SAT_TOL,
            [float(np.min(candidate_sat)), float(np.max(candidate_sat))],
        )

        candidate_reconstructed = float(
            r2.stored_co2_mass_kg(
                candidate_sat,
                pressure_psi,
                p_ref,
                CELL_PORE_VOLUME_M3,
            )
        )
        candidate_total = float(np.sum(candidate_grid))
        candidate_global_delta = candidate_total - parent_total
        global_source_sink_residual = candidate_global_delta - injected + produced

        sci_gate(
            "candidate_grid_mass_reconstruction",
            abs(candidate_reconstructed - candidate_total) <= grid_tol,
            [candidate_reconstructed, candidate_total, grid_tol],
        )
        sci_gate(
            "candidate_global_source_sink_closure",
            abs(global_source_sink_residual) <= grid_tol,
            [global_source_sink_residual, grid_tol],
        )
        sci_gate(
            "candidate_total_matches_target",
            abs(candidate_total - target_final_mass) <= grid_tol,
            [candidate_total, target_final_mass, grid_tol],
        )

        stage = "candidate_publication"
        arrays = {
            "parent_canonical_day": np.asarray(DAY, dtype=np.float64),
            "candidate_target_day": np.asarray(CANDIDATE_TARGET_DAY, dtype=np.float64),
            "candidate_dt_days": np.asarray(DT_DAYS, dtype=np.float64),
            "physical_time_committed": np.asarray(False, dtype=np.bool_),
            "candidate_state_accepted": np.asarray(False, dtype=np.bool_),
            "source_R25R3_state_sha256": np.asarray(R25R3_STATE_SHA256, dtype="U64"),
            "source_R22_flow_epoch_sha256": np.asarray(R22_EPOCH_SHA256, dtype="U64"),
            "source_pressure_epoch_sha256": np.asarray(PRESSURE_EPOCH_SHA256, dtype="U64"),
            "cartesian_component_mass_parent_kg": grid_parent,
            "cartesian_component_mass_candidate_kg": candidate_grid,
            "represented_cartesian_mass_parent_kg": represented_parent,
            "represented_cartesian_mass_candidate_kg": represented_candidate,
            "grid_residual_component_mass_parent_kg": residual_parent,
            "grid_residual_component_mass_candidate_kg": residual_candidate,
            "transport_CV_component_mass_parent_kg": old_cv_mass,
            "transport_CV_component_mass_candidate_kg": new_cv_mass,
            "transport_CV_saturation_parent": old_cv_sat,
            "transport_CV_saturation_candidate": new_cv_sat,
            "CV_to_grid_delta_component_mass_kg": delta_grid,
            "streamline_xyz_m": xyz,
            "streamline_tof_s": tof_s,
            "streamline_weight_m3_s": weights_m3_s,
            "producer_labels": producer_labels,
            "streamline_id": streamline_id,
            "refreshed_pressure_psi": pressure_psi,
            "reference_gas_pressure_pa": np.asarray(p_ref, dtype=np.float64),
            "injected_component_mass_kg": np.asarray(injected, dtype=np.float64),
            "produced_component_mass_kg": np.asarray(produced, dtype=np.float64),
            "CV_component_mass_delta_kg": np.asarray(cv_delta, dtype=np.float64),
            "candidate_cartesian_mass_delta_kg": np.asarray(candidate_global_delta, dtype=np.float64),
            "CV_transport_mass_residual_kg": np.asarray(cv_mass_residual, dtype=np.float64),
            "CV_to_grid_transfer_residual_kg": np.asarray(transfer_residual, dtype=np.float64),
            "candidate_grid_ledger_residual_kg": np.asarray(grid_ledger_residual, dtype=np.float64),
            "candidate_global_source_sink_residual_kg": np.asarray(global_source_sink_residual, dtype=np.float64),
            "candidate_max_cell_capacity_excess_kg": np.asarray(capacity_excess, dtype=np.float64),
            "candidate_min_represented_cell_mass_kg": np.asarray(min_rep_candidate, dtype=np.float64),
            "residual_sidecar_mutated": np.asarray(False, dtype=np.bool_),
            "absolute_mapback_executed": np.asarray(False, dtype=np.bool_),
            "delta_mapback_executed": np.asarray(True, dtype=np.bool_),
            "pressure_refresh_executed": np.asarray(False, dtype=np.bool_),
        }

        out.mkdir(parents=True, exist_ok=False)
        candidate_name = f"{OUT_TOKEN}_Provisional_FrozenFlow_Transport_Candidate.npz"
        candidate_path = out / candidate_name
        candidate_path.write_bytes(deterministic_npz_bytes(arrays))
        candidate_sha = sha(candidate_path)

        classification = (
            "R6R29_PROVISIONAL_FROZEN_FLOW_TRANSPORT_CANDIDATE_PASS_"
            "RESIDUAL_PRESERVED_DELTA_MAPBACK_CAPACITY_CLOSED_R30_TIME_COMMIT_AUDIT_NEXT"
        )

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": classification,
            "provisional_candidate_sha256": candidate_sha,
            "source_R25R3_state_sha256": R25R3_STATE_SHA256,
            "parent_day": DAY,
            "candidate_target_day": CANDIDATE_TARGET_DAY,
            "dt_days": DT_DAYS,
            "parent_cartesian_mass_kg": parent_total,
            "parent_transport_CV_mass_kg": old_cv_total,
            "parent_residual_mass_kg": residual_total,
            "injected_component_mass_kg": injected,
            "produced_component_mass_kg": produced,
            "CV_component_mass_delta_kg": cv_delta,
            "candidate_cartesian_mass_delta_kg": candidate_global_delta,
            "candidate_cartesian_mass_total_kg": candidate_total,
            "candidate_transport_CV_mass_total_kg": float(np.sum(new_cv_mass)),
            "candidate_residual_mass_total_kg": float(np.sum(residual_candidate)),
            "CV_transport_mass_residual_kg": cv_mass_residual,
            "CV_to_grid_transfer_residual_kg": transfer_residual,
            "candidate_grid_ledger_residual_kg": grid_ledger_residual,
            "candidate_global_source_sink_residual_kg": global_source_sink_residual,
            "candidate_max_cell_capacity_excess_kg": capacity_excess,
            "candidate_min_cartesian_cell_mass_kg": min_candidate_mass,
            "candidate_min_represented_cell_mass_kg": min_rep_candidate,
            "candidate_saturation_min": float(np.min(candidate_sat)),
            "candidate_saturation_max": float(np.max(candidate_sat)),
            "aggregate_producer_CO2_cut": aggregate_cut,
            "residual_sidecar_unchanged": True,
            "delta_mapback_executed": True,
            "absolute_mapback_executed": False,
            "transport_execution_performed": True,
            "physical_time_committed": False,
            "pressure_refresh_executed": False,
            "P3_authorized": False,
        }

        execution = {
            "milestone": M,
            "status": PASS,
            "candidate_state_sha256": candidate_sha,
            "candidate_only": True,
            "physical_time_committed": False,
            "parent_state_sha256": R25R3_STATE_SHA256,
            "frozen_flow_geometry_sha256": R22_EPOCH_SHA256,
            "frozen_pressure_epoch_sha256": PRESSURE_EPOCH_SHA256,
            "dt_days": DT_DAYS,
            "candidate_target_day": CANDIDATE_TARGET_DAY,
            "transport_implementation": "E37A.advance_component_mass_control_volumes",
            "mapback_implementation": "E37A.map_control_volume_increment_to_grid",
            "residual_direct_well_exchange_executed": False,
            "residual_sidecar_mutated": False,
            "automatic_dt_reduction_executed": False,
            "support_growth_executed": False,
            "global_source_sink_identity": "sum(M_candidate)-sum(M_parent) = M_injected - M_produced",
            "split_identity": "M_candidate = M_residual_parent + (M_represented_parent + Delta_M_grid)",
        }

        decision = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "P2_R6_R30_authorized": True,
            "P2_R6_R30_name": "Post-Day375 Frozen-Flow Transport Candidate Closure / Physical-Time Commit Acceptance Audit",
            "P2_R6_R30_design_or_diagnostic_only": True,
            "P2_R6_R30_execution_authorized": False,
            "P2_R6_R30_must_bind_R29_candidate_SHA": True,
            "P2_R6_R30_R29_candidate_sha256": candidate_sha,
            "P2_R6_R30_must_bind_R28_protocol": True,
            "candidate_state_is_provisional": True,
            "candidate_target_day": CANDIDATE_TARGET_DAY,
            "physical_time_committed_now": False,
            "pressure_refresh_authorized": False,
            "Darcy_Pollock_TOF_refresh_authorized": False,
            "transport_additional_step_authorized": False,
            "mapback_additional_execution_authorized": False,
            "P3_authorized": False,
            "P4_authorized": False,
            "P5_training_authorized": False,
        }

        (out / f"PAD_Stream_{OUT_TOKEN}_Summary.json").write_bytes(jb(summary))
        (out / f"{OUT_TOKEN}_Execution_Contract.json").write_bytes(jb(execution))
        (out / f"{OUT_TOKEN}_Producer_Component_Mass_Ledger.csv").write_bytes(csvb(producer_rows))
        (out / f"{OUT_TOKEN}_Decision_Contract.json").write_bytes(jb(decision))
        (out / f"{OUT_TOKEN}_Final_Gate_Matrix.csv").write_bytes(csvb(gates))

        manifest_rows = []
        for p in sorted(out.iterdir()):
            if p.is_file():
                manifest_rows.append({"file": p.name, "sha256": sha(p), "bytes": p.stat().st_size})
        (out / f"{OUT_TOKEN}_Artifact_Manifest.csv").write_bytes(csvb(manifest_rows))

        print("=" * 190)
        print(M, "PASS")
        print("Provisional candidate SHA256               :", candidate_sha)
        print("Parent / candidate target day              :", DAY, "/", CANDIDATE_TARGET_DAY)
        print("dt days                                    :", DT_DAYS)
        print("Injected / produced component mass kg      :", injected, "/", produced)
        print("CV / Cartesian mass delta kg               :", cv_delta, "/", candidate_global_delta)
        print("CV transport mass residual kg              :", cv_mass_residual)
        print("CV->grid transfer residual kg              :", transfer_residual)
        print("Global source/sink residual kg             :", global_source_sink_residual)
        print("Min represented candidate cell mass kg     :", min_rep_candidate)
        print("Max Cartesian capacity excess kg           :", capacity_excess)
        print("Candidate saturation min / max             :", float(np.min(candidate_sat)), "/", float(np.max(candidate_sat)))
        print("Residual sidecar unchanged                 : True")
        print("Physical time committed                    : False")
        print("R30 acceptance/time-commit audit           : AUTHORIZED")
        print("P3 authorized                              : False")
        print("=" * 190)
        return 0

    except ScientificFail as exc:
        fail_dir.mkdir(parents=True, exist_ok=True)
        p = fail_dir / f"{OUT_TOKEN}_Scientific_Fail_Report.json"
        if not p.exists():
            p.write_bytes(jb({
                "milestone": M,
                "status": SCI_FAIL,
                "failed_stage": stage,
                "failed_gate": exc.gate,
                "detail": exc.detail,
                "science_started": science_started,
                "R28_protocol_preserved": True,
                "R26_parent_acceptance_preserved": True,
                "R25R3_parent_state_preserved": True,
                "candidate_state_accepted": False,
                "physical_time_committed": False,
                "pressure_refresh_executed": False,
                "automatic_dt_reduction_authorized": False,
                "automatic_rerun_authorized": False,
                "P3_authorized": False,
                "gates_completed": gates,
            }))
        print("=" * 190)
        print(M, "SCIENTIFIC FAIL")
        print("Stage      :", stage)
        print("Failed gate:", exc.gate)
        print("Detail     :", repr(exc.detail))
        print("NO PHYSICAL-TIME COMMIT / PRESSURE REFRESH / AUTOMATIC RERUN.")
        print("=" * 190)
        return 3

    except Exception as exc:
        block_dir.mkdir(parents=True, exist_ok=True)
        p = block_dir / f"{OUT_TOKEN}_Blocked_Report.json"
        if not p.exists():
            p.write_bytes(jb({
                "milestone": M,
                "status": BLOCK,
                "failed_stage": stage,
                "exception": repr(exc),
                "science_started": science_started,
                "R28_protocol_preserved": True,
                "R26_parent_acceptance_preserved": True,
                "R25R3_parent_state_preserved": True,
                "candidate_state_accepted": False,
                "physical_time_committed": False,
                "pressure_refresh_executed": False,
                "automatic_rerun_authorized": False,
                "P3_authorized": False,
                "gates_completed": gates,
            }))
        print("=" * 190)
        print(M, "TECHNICAL / AUTHORITY BLOCK")
        print("Stage    :", stage)
        print("Exception:", repr(exc))
        print("NO PHYSICAL-TIME COMMIT / PRESSURE REFRESH / AUTOMATIC RERUN.")
        print("=" * 190)
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
