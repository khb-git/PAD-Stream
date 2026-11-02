#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, hashlib, importlib.util, inspect, io, json, subprocess, sys, zipfile
from pathlib import Path
from typing import Any
import numpy as np

M = "POSTV16-AV4-PIVOT-P2-R6-R29-R3"
NAME = "Corrected Heterogeneous-PV Frozen-Flow Transport Candidate Execution — No Time Commit"

PASS = (
    "AV4PIVOTP2R6R29R3_CORRECTED_HETEROGENEOUS_PV_FROZEN_FLOW_"
    "TRANSPORT_CANDIDATE_EXECUTION_PASS_NO_TIME_COMMIT"
)
SCI_FAIL = (
    "AV4PIVOTP2R6R29R3_CORRECTED_HETEROGENEOUS_PV_FROZEN_FLOW_"
    "TRANSPORT_CANDIDATE_SCIENTIFIC_FAIL_NO_AUTOMATIC_RERUN"
)
BLOCK = "AV4PIVOTP2R6R29R3_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "73ef7bc447e41e09c4db8311e261278d676978f6"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"
BASE_AV3 = Path("post_v16") / RID / "POSTV16_AV3_Corey_Relperm_Heterogeneity"

GRID = (15, 50, 50)
NSL = 1078
NN = 201
NCV = 200
DAY = 375.0
DAY_TO_S = 86400.0
BACKGROUND = 0.20
MAX_SATURATION = 0.80
MAX_SG = 0.60
INJECTOR_MASS_RATE_KG_DAY = 500000.0

DT_DAYS = 0.03721673128859954
CANDIDATE_TARGET_DAY = 375.0372167312886

MASS_TOL = 1e-6
SAT_TOL = 1e-10
SOURCE_SINK_REL_TOL = 1e-10

# ----------------------------------------------------------------------
# Direct corrected-execution authority.
# ----------------------------------------------------------------------
CLOSURE_REL = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R29_R2_R1_R1_R1_"
    "False_Absence_Assertion_Technical_Closure"
)
CLOSURE_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R29_R2_R1_R1_R1_Summary.json"
CLOSURE_DECISION = "POSTV16_AV4_PIVOT_P2_R6_R29_R2_R1_R1_R1_Decision_Contract.json"
CLOSURE_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R29_R2_R1_R1_R1_Artifact_Manifest.csv"
CLOSURE_STATUS = (
    "AV4PIVOTP2R6R29R2R1R1R1_FALSE_ABSENCE_ASSERTION_TECHNICAL_CLOSURE_"
    "PASS_DIRECT_R29R1R1_AUTHORITY_RECOVERED_R29R3_NEXT"
)
CLOSURE_CLASSIFICATION = (
    "R6R29R2R1R1R1_FALSE_ABSENCE_ASSERTION_CLOSED_ORIGINAL_R29R1R1_"
    "PASS_ARTIFACTS_VALIDATED_ON_REAL_DRIVE_HETEROGENEOUS_PV_DESIGN_FROZEN_R29R3_NEXT"
)

# Immutable original R29 scientific fail.
R29_FAIL_REL = BASE / "POSTV16_AV4_PIVOT_P2_R6_R29_SCIENTIFIC_FAIL"
R29_FAIL = "POSTV16_AV4_PIVOT_P2_R6_R29_Scientific_Fail_Report.json"
R29_FAIL_SHA256 = "1522b39b9e2c89cacf8899c07bcedf61a841a57ca61cc47bd41fbcd818b02209"

# ----------------------------------------------------------------------
# Accepted parent authority.
# ----------------------------------------------------------------------
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

A6E_REL = BASE_AV3 / "POSTV16_AV3_A6_E_Frozen_Checkpoint_LocalPV_R7D_Integration_Execution"
A6E_STATE = "POSTV16_AV3_A6_E_AV3CR0003_Integrated_State.npz"
A6E_STATE_SHA256 = "f9e3a7bd8c6dcc43d522e0cb99a0cede2bd212fd570085b4faf82dc71af8f803"

# ----------------------------------------------------------------------
# Repository source authorities.
# ----------------------------------------------------------------------
CLOSURE_RUNNER = (
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R29_R2_R1_R1_R1_"
    "False_Absence_Assertion_Technical_Closure.py"
)
CLOSURE_RUNNER_BLOB = "6c9b8943cb73ec195436e0cdf0f9887f2179b1be"

R29_RUNNER = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R29_Controlled_FrozenFlow_Transport_Candidate_Execution_NoTimeCommit.py"
R29_RUNNER_BLOB = "0bb9a8ce641a9769d5181503f737b1c976bc0ca2"

E37A = "PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB = "0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"
R2 = "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"
A2E = "PAD_Stream_POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution.py"
A2E_BLOB = "79a8969233b72b4543edd382a0c3d1028c6dca09"
SG7D = "PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"
SG7D_BLOB = "890088c0c0fcab415a2c7351c5079ca8ee12bf82"
SG7A = "PAD_Stream_V15SG7A_Full_Physics_TOF_Transport.py"
SG7A_BLOB = "a4dd47338e7a85f130a6a70d0a41211e38c655f8"
E36 = "PAD_Stream_V16E36_Short_Adaptive_SGSim_Rollout_and_Early_Plume_Snapshot_Validation.py"
E36_BLOB = "9ab4035c95a25bd61c649f86c82d88f059cef9e2"

SOURCE_BLOBS = {
    CLOSURE_RUNNER: CLOSURE_RUNNER_BLOB,
    R29_RUNNER: R29_RUNNER_BLOB,
    E37A: E37A_BLOB,
    R2: R2_BLOB,
    A2E: A2E_BLOB,
    SG7D: SG7D_BLOB,
    SG7A: SG7A_BLOB,
    E36: E36_BLOB,
}

OUT_TOKEN = "POSTV16_AV4_PIVOT_P2_R6_R29_R3"
OUT_REL = BASE / (OUT_TOKEN + "_Corrected_HeterogeneousPV_FrozenFlow_Transport_Candidate_Execution_NoTimeCommit")
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
    parent = np.asarray([10.0, 20.0])
    represented = np.asarray([4.0, 9.0])
    residual = parent - represented
    delta = np.asarray([1.0, -2.0])
    represented_candidate = represented + delta
    candidate = parent + delta
    assert np.allclose(candidate, residual + represented_candidate)
    assert abs((CANDIDATE_TARGET_DAY - DAY) - DT_DAYS) < 1e-12
    print("POSTV16 AV4 PIVOT P2-R6-R29-R3 structural self-test: PASS")


def main(project_root: Path, drive_root: Path) -> int:
    root = project_root.resolve()
    drive = drive_root.resolve()
    out = drive / OUT_REL
    fail_dir = drive / FAIL_REL
    block_dir = drive / BLOCK_REL
    stage = "preflight"
    gates = []
    science_started = False

    def gate(name, cond, detail=None):
        ok = bool(cond)
        gates.append({"stage": stage, "gate": name, "pass": ok, "detail": "" if detail is None else repr(detail)})
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + ("" if detail is None else f" -- {detail}"))
        if not ok:
            raise GateError(name)

    def sci_gate(name, cond, detail=None):
        ok = bool(cond)
        gates.append({"stage": stage, "gate": name, "pass": ok, "detail": "" if detail is None else repr(detail)})
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + ("" if detail is None else f" -- {detail}"))
        if not ok:
            raise ScientificFail(name, detail)

    try:
        stage = "preexisting_state_firewall"
        gate("no_preexisting_R29R3_PASS", not (out / f"PAD_Stream_{OUT_TOKEN}_Summary.json").exists())
        gate("no_preexisting_R29R3_FAIL", not (fail_dir / f"{OUT_TOKEN}_Scientific_Fail_Report.json").exists())
        gate("no_preexisting_R29R3_BLOCK", not (block_dir / f"{OUT_TOKEN}_Blocked_Report.json").exists())

        stage = "repository_authority"
        gate("branch_exact", gt(root, "branch", "--show-current") == BRANCH)
        gate("parent_is_R29R2R1R1R1_closure", gt(root, "rev-parse", "HEAD^") == PARENT)
        gate("repository_clean", gt(root, "status", "--porcelain") == "")
        for fn, expected in SOURCE_BLOBS.items():
            p = root / fn
            gate(f"{Path(fn).stem}_present", p.is_file(), str(p))
            actual = gt(root, "hash-object", str(p)) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_blob_exact", actual == expected, actual)

        stage = "R29R3_execution_authority"
        cdir = drive / CLOSURE_REL
        cm = manifest(cdir, CLOSURE_MANIFEST)
        cs = js(cdir / CLOSURE_SUMMARY)
        cd = js(cdir / CLOSURE_DECISION)

        gate("closure_status_exact", cs.get("status") == CLOSURE_STATUS, cs.get("status"))
        gate("closure_classification_exact", cs.get("classification") == CLOSURE_CLASSIFICATION, cs.get("classification"))
        gate("closure_false_absence_closed", cs.get("false_absence_assertion_closed") is True)
        gate("closure_original_R29R1R1_artifacts_present", cs.get("original_R29R1R1_artifacts_present_on_authoritative_drive") is True)
        gate("closure_R29R1R1_manifest_validated", cs.get("R29R1R1_manifest_validated") is True)
        gate("closure_heterogeneous_design_recovered", cs.get("heterogeneous_AV4_design_recovered") is True)

        gate("R29R3_authorized", cd.get("P2_R6_R29_R3_authorized") is True)
        gate("R29R3_execution_authorized", cd.get("P2_R6_R29_R3_execution_authorized") is True)
        gate("R29R3_candidate_only", cd.get("P2_R6_R29_R3_candidate_only") is True)
        gate("R29R3_dt_exact", float(cd["P2_R6_R29_R3_dt_days"]) == DT_DAYS)
        gate("R29R3_target_day_exact", float(cd["P2_R6_R29_R3_candidate_target_day"]) == CANDIDATE_TARGET_DAY)
        gate("uniform_PV_forbidden", cd.get("uniform_cartesian_PV_authorized") is False)
        gate("heterogeneous_PV_required", cd.get("heterogeneous_AV4_cartesian_PV_required") is True)
        gate("CV_transport_change_forbidden", cd.get("CV_transport_operator_change_authorized") is False)
        gate("delta_formula_change_forbidden", cd.get("subsegment_delta_formula_change_authorized") is False)
        gate("absolute_mapback_forbidden", cd.get("absolute_mapback_authorized") is False)
        gate("residual_mutation_forbidden", cd.get("residual_sidecar_mutation_authorized") is False)
        gate("automatic_dt_reduction_forbidden", cd.get("automatic_dt_reduction_authorized") is False)
        gate("support_growth_forbidden", cd.get("support_growth_authorized") is False)
        gate("time_commit_forbidden", cd.get("physical_time_advance_authorized") is False)
        gate("pressure_refresh_forbidden", cd.get("pressure_refresh_authorized") is False)

        stage = "immutable_R29_fail_binding"
        r29fail = drive / R29_FAIL_REL / R29_FAIL
        gate("R29_FAIL_exists", r29fail.is_file(), str(r29fail))
        gate("R29_FAIL_SHA_exact", sha(r29fail) == R29_FAIL_SHA256, sha(r29fail) if r29fail.is_file() else "missing")

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
        gate("parent_split_identity", float(np.max(np.abs(grid_parent - represented_parent - residual_parent))) <= MASS_TOL)

        parent_total = float(np.sum(grid_parent))
        old_cv_total = float(np.sum(old_cv_mass))
        residual_total = float(np.sum(residual_parent))

        stage = "source_physics_binding"
        e37a = load_module(root / E37A, "r29r3_e37a")
        r2 = load_module(root / R2, "r29r3_r2")
        a2e = load_module(root / A2E, "r29r3_a2e")
        sg7d = load_module(root / SG7D, "r29r3_sg7d")
        sg7a = load_module(root / SG7A, "r29r3_sg7a")
        e36 = load_module(root / E36, "r29r3_e36")

        a6e_path = drive / A6E_REL / A6E_STATE
        gate("A6E_porosity_state_SHA_exact", a6e_path.is_file() and sha(a6e_path) == A6E_STATE_SHA256)
        with np.load(a6e_path, allow_pickle=False) as z:
            phi = np.asarray(z["paired_porosity"], dtype=np.float64)
        gate("paired_porosity_shape_positive", phi.shape == GRID and np.all(phi > 0.0) and np.isfinite(phi).all())

        hetero_pv = phi * float(a2e.BULK_VOLUME_M3)

        op = sg7d.build_subsegment_operator(xyz, tof_s / DAY_TO_S, weights_m3_s * DAY_TO_S)
        geometry = e37a.build_control_volume_geometry(r2, op, pressure_psi, p_ref, NSL, NCV)
        face_pressure = e37a.build_face_pressure(e36, sg7d, xyz, pressure_psi)
        gate("face_pressure_shape_exact", face_pressure.shape == (NSL, NCV + 1))

        xi_faces = np.linspace(0.0, 1.0, NCV + 1, dtype=np.float64)
        weights_m3_day = weights_m3_s * DAY_TO_S

        stage = "heterogeneous_parent_cartesian_validation"
        try:
            parent_sg = np.asarray(
                a2e.invert_local_mass(r2, grid_parent, pressure_psi, p_ref, hetero_pv),
                dtype=np.float64,
            )
        except Exception as exc:
            raise ScientificFail("heterogeneous_parent_cartesian_mass_inversion", repr(exc)) from exc

        parent_sat = float(a2e.BACKGROUND) + parent_sg
        parent_reconstructed = np.asarray(
            a2e.local_mass(r2, parent_sat, pressure_psi, p_ref, hetero_pv),
            dtype=np.float64,
        )
        parent_mass_err = float(np.max(np.abs(parent_reconstructed - grid_parent)))

        science_started = True
        sci_gate("heterogeneous_parent_cellwise_mass_reconstruction", parent_mass_err <= 1e-8, parent_mass_err)
        sci_gate(
            "heterogeneous_parent_saturation_bounds",
            float(np.min(parent_sat)) >= BACKGROUND - SAT_TOL
            and float(np.max(parent_sat)) <= MAX_SATURATION + SAT_TOL,
            [float(np.min(parent_sat)), float(np.max(parent_sat))],
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
        cv_tol = max(MASS_TOL, SOURCE_SINK_REL_TOL * max(abs(injected), abs(cv_delta), 1.0))

        sci_gate("CV_new_mass_shape_exact", new_cv_mass.shape == (NSL, NCV))
        sci_gate("CV_new_saturation_shape_exact", new_cv_sat.shape == (NSL, NCV))
        sci_gate("CV_mass_nonnegative", float(np.min(new_cv_mass)) >= -MASS_TOL, float(np.min(new_cv_mass)))
        sci_gate(
            "CV_saturation_bounds",
            float(np.min(new_cv_sat)) >= BACKGROUND - SAT_TOL
            and float(np.max(new_cv_sat)) <= MAX_SATURATION + SAT_TOL,
            [float(np.min(new_cv_sat)), float(np.max(new_cv_sat))],
        )
        sci_gate("injected_mass_exact_fixed_rate", abs(injected - expected_injected) <= cv_tol, [injected, expected_injected, cv_tol])
        sci_gate("produced_mass_nonnegative", produced >= -MASS_TOL, produced)
        sci_gate("CV_global_source_sink_closure", abs(cv_mass_residual) <= cv_tol, [cv_mass_residual, cv_tol])

        producer_rows, aggregate_cut = e37a.producer_rows_from_flux(
            producer_labels,
            weights_m3_day,
            transport["outlet_fractional_flow"],
            face_mass_flux[:, -1],
            DT_DAYS,
        )
        producer_rows_total = float(sum(float(r["CO2_mass_this_step_kg"]) for r in producer_rows))
        sci_gate("producer_rows_all_four_present", len(producer_rows) == 4, [r["producer"] for r in producer_rows])
        sci_gate("producer_rows_mass_matches_transport", abs(producer_rows_total - produced) <= cv_tol, [producer_rows_total, produced])
        sci_gate("aggregate_producer_CO2_cut_bounded", 0.0 <= aggregate_cut <= 1.0, aggregate_cut)

        # ------------------------------------------------------------------
        # Corrected delta-only mapback: reuse E37A formula, bypass legacy
        # scalar-PV Cartesian reconstruction/inversion.
        # ------------------------------------------------------------------
        stage = "corrected_delta_only_mapback"
        cv_id = np.asarray(geometry["cv_id"], dtype=np.int64)
        flat_cell = np.asarray(geometry["flat_cell"], dtype=np.int64)
        sub_pv = np.asarray(geometry["pv_m3"], dtype=np.float64)
        pseg = np.asarray(geometry["pseg_psi"], dtype=np.float64)

        old_flat_sat = old_cv_sat.reshape(-1)
        new_flat_sat = new_cv_sat.reshape(-1)
        old_sub_sat = old_flat_sat[cv_id]
        new_sub_sat = new_flat_sat[cv_id]
        old_sub_sg = np.clip(old_sub_sat - BACKGROUND, 0.0, MAX_SG)
        new_sub_sg = np.clip(new_sub_sat - BACKGROUND, 0.0, MAX_SG)

        rho_old = np.asarray(r2.gas_density_from_state(old_sub_sat, pseg, p_ref), dtype=np.float64)
        rho_new = np.asarray(r2.gas_density_from_state(new_sub_sat, pseg, p_ref), dtype=np.float64)

        sub_delta_mass = sub_pv * (rho_new * new_sub_sg - rho_old * old_sub_sg)
        delta_grid = np.bincount(
            flat_cell,
            weights=sub_delta_mass,
            minlength=int(np.prod(GRID)),
        ).reshape(GRID)

        sub_delta_total = float(np.sum(sub_delta_mass))
        delta_grid_total = float(np.sum(delta_grid))
        transfer_residual = sub_delta_total - cv_delta
        deposit_residual = delta_grid_total - sub_delta_total
        grid_tol = max(MASS_TOL, SOURCE_SINK_REL_TOL * max(abs(cv_delta), abs(parent_total), 1.0))

        sci_gate("subsegment_delta_matches_CV_delta", abs(transfer_residual) <= grid_tol, [sub_delta_total, cv_delta, transfer_residual, grid_tol])
        sci_gate("flat_cell_deposition_closure", abs(deposit_residual) <= grid_tol, [delta_grid_total, sub_delta_total, deposit_residual, grid_tol])
        sci_gate("delta_grid_shape_exact", delta_grid.shape == GRID)

        stage = "split_state_candidate"
        represented_candidate = represented_parent + delta_grid
        residual_candidate = residual_parent.copy()
        candidate_grid = grid_parent + delta_grid

        min_rep_candidate = float(np.min(represented_candidate))
        min_candidate_mass = float(np.min(candidate_grid))
        split_err = float(np.max(np.abs(candidate_grid - represented_candidate - residual_candidate)))

        sci_gate("represented_grid_candidate_nonnegative", min_rep_candidate >= -MASS_TOL, min_rep_candidate)
        sci_gate("candidate_cartesian_mass_nonnegative", min_candidate_mass >= -MASS_TOL, min_candidate_mass)
        sci_gate("residual_sidecar_valuewise_unchanged", np.array_equal(residual_candidate, residual_parent))
        sci_gate("candidate_split_recomposition", split_err <= MASS_TOL, split_err)

        stage = "heterogeneous_candidate_capacity_and_inversion"
        full_sat = np.full(GRID, float(a2e.INJECTED), dtype=np.float64)
        capacity_grid = np.asarray(
            a2e.local_mass(r2, full_sat, pressure_psi, p_ref, hetero_pv),
            dtype=np.float64,
        )
        cap_tol = max(1e-8, 1e-12 * max(float(np.max(capacity_grid)), 1.0))
        capacity_excess = float(np.max(candidate_grid - capacity_grid))
        sci_gate("candidate_cartesian_cell_pressure_capacity", capacity_excess <= cap_tol, [capacity_excess, cap_tol])

        try:
            candidate_sg = np.asarray(
                a2e.invert_local_mass(r2, candidate_grid, pressure_psi, p_ref, hetero_pv),
                dtype=np.float64,
            )
        except Exception as exc:
            raise ScientificFail("heterogeneous_candidate_cartesian_mass_inversion", repr(exc)) from exc

        candidate_sat = float(a2e.BACKGROUND) + candidate_sg
        reconstructed_candidate = np.asarray(
            a2e.local_mass(r2, candidate_sat, pressure_psi, p_ref, hetero_pv),
            dtype=np.float64,
        )
        candidate_cellwise_mass_err = float(np.max(np.abs(reconstructed_candidate - candidate_grid)))

        sci_gate("candidate_cellwise_mass_reconstruction", candidate_cellwise_mass_err <= 1e-8, candidate_cellwise_mass_err)
        sci_gate(
            "candidate_saturation_bounds",
            float(np.min(candidate_sat)) >= BACKGROUND - SAT_TOL
            and float(np.max(candidate_sat)) <= MAX_SATURATION + SAT_TOL,
            [float(np.min(candidate_sat)), float(np.max(candidate_sat))],
        )

        target_final_mass = parent_total + injected - produced
        candidate_total = float(np.sum(candidate_grid))
        candidate_global_delta = candidate_total - parent_total
        grid_ledger_residual = candidate_total - target_final_mass
        global_source_sink_residual = candidate_global_delta - injected + produced

        sci_gate("candidate_total_matches_target", abs(grid_ledger_residual) <= grid_tol, [candidate_total, target_final_mass, grid_ledger_residual, grid_tol])
        sci_gate("candidate_global_source_sink_closure", abs(global_source_sink_residual) <= grid_tol, [global_source_sink_residual, grid_tol])
        sci_gate("CV_and_cartesian_delta_match", abs(candidate_global_delta - cv_delta) <= grid_tol, [candidate_global_delta, cv_delta, grid_tol])

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
            "source_A6E_porosity_state_sha256": np.asarray(A6E_STATE_SHA256, dtype="U64"),
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
            "cartesian_saturation_parent": parent_sat,
            "cartesian_saturation_candidate": candidate_sat,
            "heterogeneous_pore_volume_m3": hetero_pv,
            "paired_porosity": phi,
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
            "CV_to_subsegment_transfer_residual_kg": np.asarray(transfer_residual, dtype=np.float64),
            "subsegment_to_grid_deposition_residual_kg": np.asarray(deposit_residual, dtype=np.float64),
            "candidate_grid_ledger_residual_kg": np.asarray(grid_ledger_residual, dtype=np.float64),
            "candidate_global_source_sink_residual_kg": np.asarray(global_source_sink_residual, dtype=np.float64),
            "candidate_max_cell_capacity_excess_kg": np.asarray(capacity_excess, dtype=np.float64),
            "candidate_capacity_tolerance_kg": np.asarray(cap_tol, dtype=np.float64),
            "candidate_cellwise_mass_reconstruction_error_kg": np.asarray(candidate_cellwise_mass_err, dtype=np.float64),
            "candidate_min_represented_cell_mass_kg": np.asarray(min_rep_candidate, dtype=np.float64),
            "residual_sidecar_mutated": np.asarray(False, dtype=np.bool_),
            "legacy_absolute_mapback_executed": np.asarray(False, dtype=np.bool_),
            "legacy_scalar_cartesian_PV_executed": np.asarray(False, dtype=np.bool_),
            "delta_only_mapback_executed": np.asarray(True, dtype=np.bool_),
            "pressure_refresh_executed": np.asarray(False, dtype=np.bool_),
        }

        out.mkdir(parents=True, exist_ok=False)
        candidate_name = f"{OUT_TOKEN}_Provisional_Corrected_HeterogeneousPV_Transport_Candidate.npz"
        candidate_path = out / candidate_name
        candidate_path.write_bytes(deterministic_npz_bytes(arrays))
        candidate_sha = sha(candidate_path)

        classification = (
            "R6R29R3_CORRECTED_HETEROGENEOUS_PV_FROZEN_FLOW_TRANSPORT_CANDIDATE_PASS_"
            "RESIDUAL_PRESERVED_DELTA_ONLY_MAPBACK_CAPACITY_CLOSED_R30_ACCEPTANCE_NEXT"
        )

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": classification,
            "provisional_candidate_sha256": candidate_sha,
            "source_R29_scientific_fail_sha256": R29_FAIL_SHA256,
            "source_R25R3_state_sha256": R25R3_STATE_SHA256,
            "source_A6E_porosity_state_sha256": A6E_STATE_SHA256,
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
            "CV_to_subsegment_transfer_residual_kg": transfer_residual,
            "subsegment_to_grid_deposition_residual_kg": deposit_residual,
            "candidate_grid_ledger_residual_kg": grid_ledger_residual,
            "candidate_global_source_sink_residual_kg": global_source_sink_residual,
            "candidate_max_cell_capacity_excess_kg": capacity_excess,
            "candidate_capacity_tolerance_kg": cap_tol,
            "candidate_cellwise_mass_reconstruction_error_kg": candidate_cellwise_mass_err,
            "candidate_min_cartesian_cell_mass_kg": min_candidate_mass,
            "candidate_min_represented_cell_mass_kg": min_rep_candidate,
            "candidate_saturation_min": float(np.min(candidate_sat)),
            "candidate_saturation_max": float(np.max(candidate_sat)),
            "aggregate_producer_CO2_cut": aggregate_cut,
            "residual_sidecar_unchanged": True,
            "delta_only_mapback_executed": True,
            "legacy_absolute_mapback_executed": False,
            "legacy_scalar_cartesian_PV_executed": False,
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
            "heterogeneous_porosity_state_sha256": A6E_STATE_SHA256,
            "dt_days": DT_DAYS,
            "candidate_target_day": CANDIDATE_TARGET_DAY,
            "transport_implementation": "E37A.advance_component_mass_control_volumes",
            "mapback_implementation": "local exact E37A subsegment-delta formula + flat-cell deposition only",
            "cartesian_closure_implementation": "A2E.local_mass + A2E.invert_local_mass with heterogeneous pore-volume array",
            "legacy_E37A_full_mapback_called": False,
            "legacy_uniform_cartesian_PV_used": False,
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
            "P2_R6_R30_name": "Corrected Post-Day375 Frozen-Flow Transport Candidate Closure / Physical-Time Commit Acceptance Audit",
            "P2_R6_R30_design_or_diagnostic_only": True,
            "P2_R6_R30_execution_authorized": False,
            "P2_R6_R30_must_bind_R29R3_candidate_SHA": True,
            "P2_R6_R30_R29R3_candidate_sha256": candidate_sha,
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

        rows = []
        for p in sorted(out.iterdir()):
            if p.is_file():
                rows.append({"file": p.name, "sha256": sha(p), "bytes": p.stat().st_size})
        (out / f"{OUT_TOKEN}_Artifact_Manifest.csv").write_bytes(csvb(rows))

        print("=" * 190)
        print(M, "PASS")
        print("Provisional candidate SHA256            :", candidate_sha)
        print("Parent / candidate target day           :", DAY, "/", CANDIDATE_TARGET_DAY)
        print("dt days                                 :", DT_DAYS)
        print("Injected / produced component mass kg   :", injected, "/", produced)
        print("CV / Cartesian mass delta kg            :", cv_delta, "/", candidate_global_delta)
        print("CV transport residual kg                :", cv_mass_residual)
        print("CV->subsegment residual kg              :", transfer_residual)
        print("Subsegment->grid residual kg            :", deposit_residual)
        print("Global source/sink residual kg          :", global_source_sink_residual)
        print("Max heterogeneous capacity excess kg    :", capacity_excess)
        print("Heterogeneous capacity tolerance kg     :", cap_tol)
        print("Candidate saturation min / max          :", float(np.min(candidate_sat)), "/", float(np.max(candidate_sat)))
        print("Residual sidecar unchanged              : True")
        print("Legacy scalar Cartesian PV used         : False")
        print("Physical time committed                 : False")
        print("R30 acceptance audit                    : AUTHORIZED")
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
                "source_R29_SCIENTIFIC_FAIL_preserved": True,
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
