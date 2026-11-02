#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, hashlib, importlib.util, io, json, subprocess, sys, zipfile
from pathlib import Path
from typing import Any
import numpy as np

M = "POSTV16-AV4-PIVOT-P2-R6-R29-R3-R2"
NAME = "Capacity-Constrained Face-Flux Repair Feasibility + Comprehensive Design Freeze"

PASS = (
    "AV4PIVOTP2R6R29R3R2_CAPACITY_CONSTRAINED_FACE_FLUX_REPAIR_"
    "FEASIBILITY_AND_COMPREHENSIVE_DESIGN_FREEZE_PASS_NO_STATE_MUTATION"
)
BLOCK = "AV4PIVOTP2R6R29R3R2_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "2260794c63ec4bd0bd036381b373f4f370ebe741"

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
DT_NOMINAL = 0.03721673128859954
TARGET_NOMINAL = 375.0372167312886
MASS_TOL = 1e-6
SAT_TOL = 1e-10
SOURCE_SINK_REL_TOL = 1e-10

# ----------------------------------------------------------------------
# R29-R3-R1 propagation-audit authority.
# ----------------------------------------------------------------------
R1_REL = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R29_R3_R1_"
    "CV_Capacity_Localization_and_Full_Downstream_Propagation_Audit"
)
R1_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R29_R3_R1_Summary.json"
R1_DECISION = "POSTV16_AV4_PIVOT_P2_R6_R29_R3_R1_Decision_Contract.json"
R1_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R29_R3_R1_Artifact_Manifest.csv"
R1_ARRAYS = "POSTV16_AV4_PIVOT_P2_R6_R29_R3_R1_Full_CV_Capacity_and_Propagation_Audit.npz"
R1_STATUS = (
    "AV4PIVOTP2R6R29R3R1_CV_CAPACITY_LOCALIZATION_AND_FULL_DOWNSTREAM_"
    "PROPAGATION_AUDIT_PASS_NO_STATE_MUTATION"
)
R1_CLASSIFICATION = (
    "NOMINAL_DT_LOCAL_CV_CAPACITY_LIMIT_WITH_ADDITIONAL_DOWNSTREAM_"
    "INCOMPATIBILITY_DETECTED_BY_PROPAGATION_PROBE"
)
R29R3_FAIL_SHA256 = "c533e9b5925a4e1fc4f970d1630084a375de1d839207413267eb547bcfb7754b"

# Accepted parent.
R25R3_REL = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R25_R3_"
    "Controlled_Day375_CapacityLimited_ExactSupport_SplitState_"
    "Reprojection_Execution_Stage2_PresolveOff"
)
R25R3_STATE = "POSTV16_AV4_PIVOT_P2_R6_R25_R3_CapacityLimited_SplitState_Day375.npz"
R25R3_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R25_R3_Artifact_Manifest.csv"
R25R3_STATE_SHA256 = "9893e2476bce1d46213cdd1304e60ad93b49ea285e084d06743a2ffab25f721f"

A6E_REL = BASE_AV3 / "POSTV16_AV3_A6_E_Frozen_Checkpoint_LocalPV_R7D_Integration_Execution"
A6E_STATE = "POSTV16_AV3_A6_E_AV3CR0003_Integrated_State.npz"
A6E_STATE_SHA256 = "f9e3a7bd8c6dcc43d522e0cb99a0cede2bd212fd570085b4faf82dc71af8f803"

# Frozen source authorities.
R1_RUNNER = (
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R29_R3_R1_"
    "CV_Capacity_Localization_and_Full_Downstream_Propagation_Audit.py"
)
R1_RUNNER_BLOB = "fd353b56e819ee1cf996eb7f861cbbd274e2b861"
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
    R1_RUNNER: R1_RUNNER_BLOB,
    E37A: E37A_BLOB,
    R2: R2_BLOB,
    A2E: A2E_BLOB,
    SG7D: SG7D_BLOB,
    SG7A: SG7A_BLOB,
    E36: E36_BLOB,
}

OUT_TOKEN = "POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2"
OUT_REL = BASE / (
    OUT_TOKEN + "_Capacity_Constrained_FaceFlux_Repair_Feasibility_and_Comprehensive_Design_Freeze"
)
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
    # Saturated cell with positive nominal accumulation:
    m = 10.0
    cap = 10.0
    fin = 5.0
    fnom = 4.0
    fmax = 6.0
    dt = 0.1
    lower = fin - (cap - m) / dt
    upper = fin + m / dt
    lo = max(0.0, lower)
    hi = min(upper, fmax)
    fout = min(max(fnom, lo), hi)
    assert fout == 5.0
    assert abs(m + dt * (fin - fout) - cap) < 1e-14
    print("POSTV16 AV4 PIVOT P2-R6-R29-R3-R2 structural self-test: PASS")


def main(project_root: Path, drive_root: Path) -> int:
    root = project_root.resolve()
    drive = drive_root.resolve()
    out = drive / OUT_REL
    block_dir = drive / BLOCK_REL
    stage = "preflight"
    gates = []

    def gate(name: str, cond: Any, detail: Any = None) -> None:
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
        gate("no_preexisting_R29R3R2_PASS", not (out / f"PAD_Stream_{OUT_TOKEN}_Summary.json").exists())
        gate("no_preexisting_R29R3R2_BLOCK", not (block_dir / f"{OUT_TOKEN}_Blocked_Report.json").exists())

        stage = "repository_authority"
        gate("branch_exact", gt(root, "branch", "--show-current") == BRANCH)
        gate("parent_is_R29R3R1_commit", gt(root, "rev-parse", "HEAD^") == PARENT)
        gate("repository_clean", gt(root, "status", "--porcelain") == "")
        for fn, expected in SOURCE_BLOBS.items():
            p = root / fn
            gate(f"{Path(fn).stem}_present", p.is_file(), str(p))
            actual = gt(root, "hash-object", str(p)) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_blob_exact", actual == expected, actual)

        stage = "R29R3R1_audit_authority"
        r1 = drive / R1_REL
        mm = manifest(r1, R1_MANIFEST)
        s1 = js(r1 / R1_SUMMARY)
        d1 = js(r1 / R1_DECISION)
        gate("R1_status_exact", s1.get("status") == R1_STATUS, s1.get("status"))
        gate("R1_classification_exact", s1.get("classification") == R1_CLASSIFICATION, s1.get("classification"))
        gate("R1_FAIL_SHA_exact", s1.get("source_R29R3_scientific_fail_sha256") == R29R3_FAIL_SHA256)
        gate("R1_parent_CV_valid", int(s1.get("parent_CV_capacity_violation_count")) == 0)
        gate(
            "R1_parent_CV_mass_sat_consistent",
            float(s1.get("parent_CV_mass_saturation_max_abs_error_kg"))
            <= float(s1.get("parent_CV_mass_saturation_tolerance_kg")),
        )
        gate("R1_nominal_violation_count_positive", int(s1.get("nominal_CV_capacity_violation_count")) > 0)
        gate("R1_zero_capacity_dt", float(s1.get("global_capacity_limited_dt_days")) == 0.0)
        gate("R1_probe_not_possible", s1.get("diagnostic_capacity_feasible_probe", {}).get("probe_possible") is False)
        gate("R1_R2_authorized", d1.get("P2_R6_R29_R3_R2_authorized") is True)
        gate("R1_R2_design_only", d1.get("P2_R6_R29_R3_R2_design_only") is True)
        gate("R1_R2_execution_forbidden", d1.get("P2_R6_R29_R3_R2_execution_authorized") is False)
        gate("R1_arrays_in_manifest", R1_ARRAYS in mm)

        with np.load(r1 / R1_ARRAYS, allow_pickle=False) as z:
            old_cv_mass = np.asarray(z["old_CV_mass_kg"], dtype=np.float64)
            old_cv_sat = np.asarray(z["old_CV_saturation"], dtype=np.float64)
            cv_capacity = np.asarray(z["CV_capacity_kg"], dtype=np.float64)
            nominal_face_flux = np.asarray(z["face_mass_flux_kg_day"], dtype=np.float64)
            nominal_excess = np.asarray(z["nominal_CV_capacity_excess_kg"], dtype=np.float64)

        gate(
            "R1_array_shapes_exact",
            old_cv_mass.shape == (NSL, NCV)
            and old_cv_sat.shape == (NSL, NCV)
            and cv_capacity.shape == (NSL, NCV)
            and nominal_face_flux.shape == (NSL, NCV + 1),
        )

        stage = "accepted_parent_and_geometry_authority"
        r25 = drive / R25R3_REL
        m25 = manifest(r25, R25R3_MANIFEST)
        state_path = r25 / R25R3_STATE
        gate("R25R3_state_manifest_SHA_exact", m25.get(R25R3_STATE) == R25R3_STATE_SHA256)
        gate("R25R3_state_file_SHA_exact", sha(state_path) == R25R3_STATE_SHA256)

        with np.load(state_path, allow_pickle=False) as z:
            grid_parent = np.asarray(z["cartesian_component_mass_kg"], dtype=np.float64)
            represented_parent = np.asarray(z["represented_cartesian_cell_mass_kg"], dtype=np.float64)
            residual_parent = np.asarray(z["grid_residual_component_mass_kg"], dtype=np.float64)
            xyz = np.asarray(z["streamline_xyz_m"], dtype=np.float64)
            tof_s = np.asarray(z["streamline_tof_s"], dtype=np.float64)
            weights_m3_s = np.asarray(z["streamline_weight_m3_s"], dtype=np.float64)
            producer_labels = np.asarray(z["producer_labels"]).astype("U32")
            streamline_id = np.asarray(z["streamline_id"], dtype=np.int64)
            pressure_psi = np.asarray(z["refreshed_pressure_psi"], dtype=np.float64)
            p_ref = float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))

        e37a = load_module(root / E37A, "r29r3r2_e37a")
        r2 = load_module(root / R2, "r29r3r2_r2")
        a2e = load_module(root / A2E, "r29r3r2_a2e")
        sg7d = load_module(root / SG7D, "r29r3r2_sg7d")
        sg7a = load_module(root / SG7A, "r29r3r2_sg7a")
        e36 = load_module(root / E36, "r29r3r2_e36")

        a6e_path = drive / A6E_REL / A6E_STATE
        gate("A6E_state_SHA_exact", a6e_path.is_file() and sha(a6e_path) == A6E_STATE_SHA256)
        with np.load(a6e_path, allow_pickle=False) as z:
            phi = np.asarray(z["paired_porosity"], dtype=np.float64)
        hetero_pv = phi * float(a2e.BULK_VOLUME_M3)

        op = sg7d.build_subsegment_operator(xyz, tof_s / DAY_TO_S, weights_m3_s * DAY_TO_S)
        geometry = e37a.build_control_volume_geometry(r2, op, pressure_psi, p_ref, NSL, NCV)
        face_pressure = e37a.build_face_pressure(e36, sg7d, xyz, pressure_psi)
        gate("face_pressure_shape_exact", face_pressure.shape == (NSL, NCV + 1))

        # ------------------------------------------------------------------
        # Physical face-flux envelope.
        #
        # For fixed q and face pressure, the transported component flux is
        # q*u_face*f(S)*rho(S,p_face). The p_face factor is multiplicative in
        # the EOS, so monotonicity with saturation can be certified once.
        # ------------------------------------------------------------------
        stage = "physical_face_flux_envelope"
        sat_scan = np.linspace(float(sg7a.S_INITIAL), float(sg7a.S_INJECTED), 4001)
        ff_scan = np.asarray(sg7a.fractional_flow(sat_scan), dtype=np.float64)
        rho_scan = np.asarray(
            r2.gas_density_from_state(
                sat_scan,
                np.full_like(sat_scan, float(np.mean(face_pressure))),
                p_ref,
            ),
            dtype=np.float64,
        )
        component_factor = ff_scan * rho_scan
        min_component_factor_diff = float(np.min(np.diff(component_factor)))
        gate(
            "component_flux_factor_monotone_to_injected_endpoint",
            min_component_factor_diff >= -1e-10,
            min_component_factor_diff,
        )

        xi_faces = np.linspace(0.0, 1.0, NCV + 1, dtype=np.float64)
        u_face = np.asarray(sg7a.u_dimensionless(xi_faces), dtype=np.float64)
        weights_m3_day = weights_m3_s * DAY_TO_S

        max_sat = np.full((NSL, NCV), float(sg7a.S_INJECTED), dtype=np.float64)
        rho_face_max = np.asarray(
            r2.gas_density_from_state(
                max_sat,
                face_pressure[:, 1:],
                p_ref,
            ),
            dtype=np.float64,
        )
        ff_max = float(np.asarray(sg7a.fractional_flow(np.asarray([sg7a.S_INJECTED])))[0])
        physical_max_face_flux = (
            weights_m3_day[:, None]
            * u_face[None, 1:]
            * ff_max
            * rho_face_max
        )

        # ------------------------------------------------------------------
        # Prospective conservative capacity-constrained face-flux projection.
        #
        # Inlet component flux is frozen exactly.
        # For CV i:
        #   Mnew = Mold + dt (Fin - Fout)
        # and require 0 <= Mnew <= C.
        #
        # Therefore:
        #   Fout >= Fin - (C-Mold)/dt
        #   Fout <= Fin + Mold/dt
        #
        # Intersect with physical face envelope 0 <= Fout <= Fmax.
        # Select the feasible Fout closest to the nominal explicit flux.
        #
        # One-way positive streamline flow makes the forward sweep causal.
        # ------------------------------------------------------------------
        stage = "capacity_constrained_face_flux_feasibility"
        adjusted_flux = np.asarray(nominal_face_flux, dtype=np.float64).copy()
        adjusted_flux[:, 0] = nominal_face_flux[:, 0]  # exact source preservation

        lower_required = np.zeros((NSL, NCV), dtype=np.float64)
        upper_allowed = np.zeros((NSL, NCV), dtype=np.float64)
        lower_feasible = np.zeros((NSL, NCV), dtype=np.float64)
        upper_feasible = np.zeros((NSL, NCV), dtype=np.float64)
        infeasible_mask = np.zeros((NSL, NCV), dtype=bool)

        flux_scale = max(float(np.max(np.abs(nominal_face_flux))), 1.0)
        flux_tol = max(1e-10, 1e-12 * flux_scale)

        for cv in range(NCV):
            fin = adjusted_flux[:, cv]
            lower = fin - (cv_capacity[:, cv] - old_cv_mass[:, cv]) / DT_NOMINAL
            upper = fin + old_cv_mass[:, cv] / DT_NOMINAL
            lo = np.maximum(0.0, lower)
            hi = np.minimum(upper, physical_max_face_flux[:, cv])

            lower_required[:, cv] = lower
            upper_allowed[:, cv] = upper
            lower_feasible[:, cv] = lo
            upper_feasible[:, cv] = hi

            bad = lo > hi + flux_tol
            infeasible_mask[:, cv] = bad

            nominal_out = nominal_face_flux[:, cv + 1]
            adjusted = np.minimum(np.maximum(nominal_out, lo), hi)
            # For infeasible cells, retain nominal only as a diagnostic placeholder.
            adjusted = np.where(bad, nominal_out, adjusted)
            adjusted_flux[:, cv + 1] = adjusted

        infeasible_count = int(np.count_nonzero(infeasible_mask))
        prospective_feasible = infeasible_count == 0

        correction = adjusted_flux - nominal_face_flux
        corrected_face_mask = np.abs(correction) > flux_tol
        corrected_face_count = int(np.count_nonzero(corrected_face_mask))
        max_abs_flux_correction = float(np.max(np.abs(correction)))
        l1_flux_correction = float(np.sum(np.abs(correction)))

        prospective_new_mass = old_cv_mass + DT_NOMINAL * (
            adjusted_flux[:, :-1] - adjusted_flux[:, 1:]
        )
        prospective_capacity_excess = prospective_new_mass - cv_capacity
        prospective_max_capacity_excess = float(np.max(prospective_capacity_excess))
        prospective_min_mass = float(np.min(prospective_new_mass))

        mass_tol = max(1e-6, 1e-10 * max(float(np.sum(old_cv_mass)), 1.0))
        capacity_tol = max(
            1e-9,
            1e-12 * max(float(np.max(np.abs(prospective_new_mass))), 1.0),
        )

        injected = float(np.sum(adjusted_flux[:, 0]) * DT_NOMINAL)
        produced_nominal = float(np.sum(nominal_face_flux[:, -1]) * DT_NOMINAL)
        produced_adjusted = float(np.sum(adjusted_flux[:, -1]) * DT_NOMINAL)
        prospective_cv_delta = float(np.sum(prospective_new_mass) - np.sum(old_cv_mass))
        prospective_cv_residual = prospective_cv_delta - injected + produced_adjusted

        # ------------------------------------------------------------------
        # Full downstream propagation at ORIGINAL nominal dt, but prospective
        # and non-authoritative. This is the key closure test.
        # ------------------------------------------------------------------
        stage = "prospective_full_downstream_closure"
        downstream = {
            "face_flux_projection_feasible": prospective_feasible,
            "CV_nonnegative_pass": False,
            "CV_capacity_pass": False,
            "CV_source_sink_closure_pass": False,
            "CV_inversion_pass": False,
            "CV_to_subsegment_closure_pass": False,
            "subsegment_to_grid_closure_pass": False,
            "represented_nonnegative_pass": False,
            "split_identity_pass": False,
            "heterogeneous_cartesian_capacity_pass": False,
            "heterogeneous_cartesian_inversion_pass": False,
            "cartesian_source_sink_closure_pass": False,
            "all_downstream_checks_pass": False,
            "exception": None,
        }
        prospective_arrays = {}

        if prospective_feasible:
            try:
                downstream["CV_nonnegative_pass"] = prospective_min_mass >= -mass_tol
                downstream["CV_capacity_pass"] = prospective_max_capacity_excess <= capacity_tol
                downstream["CV_source_sink_closure_pass"] = abs(prospective_cv_residual) <= mass_tol

                prospective_sat = np.asarray(
                    e37a.invert_cv_mass_to_saturation(
                        r2,
                        prospective_new_mass,
                        np.asarray(geometry["cv_pressure_mass_coeff"], dtype=np.float64),
                    ),
                    dtype=np.float64,
                )
                downstream["CV_inversion_pass"] = True

                cv_id = np.asarray(geometry["cv_id"], dtype=np.int64)
                flat_cell = np.asarray(geometry["flat_cell"], dtype=np.int64)
                sub_pv = np.asarray(geometry["pv_m3"], dtype=np.float64)
                pseg = np.asarray(geometry["pseg_psi"], dtype=np.float64)

                old_sub_sat = old_cv_sat.reshape(-1)[cv_id]
                new_sub_sat = prospective_sat.reshape(-1)[cv_id]
                old_sub_sg = np.clip(old_sub_sat - BACKGROUND, 0.0, MAX_SG)
                new_sub_sg = np.clip(new_sub_sat - BACKGROUND, 0.0, MAX_SG)
                rho_old = np.asarray(r2.gas_density_from_state(old_sub_sat, pseg, p_ref), dtype=np.float64)
                rho_new = np.asarray(r2.gas_density_from_state(new_sub_sat, pseg, p_ref), dtype=np.float64)
                sub_delta_mass = sub_pv * (
                    rho_new * new_sub_sg - rho_old * old_sub_sg
                )

                sub_delta = float(np.sum(sub_delta_mass))
                transfer_residual = sub_delta - prospective_cv_delta
                grid_tol = max(
                    MASS_TOL,
                    SOURCE_SINK_REL_TOL * max(
                        abs(prospective_cv_delta),
                        float(np.sum(grid_parent)),
                        1.0,
                    ),
                )
                downstream["CV_to_subsegment_closure_pass"] = abs(transfer_residual) <= grid_tol

                delta_grid = np.bincount(
                    flat_cell,
                    weights=sub_delta_mass,
                    minlength=int(np.prod(GRID)),
                ).reshape(GRID)
                deposit_residual = float(np.sum(delta_grid) - sub_delta)
                downstream["subsegment_to_grid_closure_pass"] = abs(deposit_residual) <= grid_tol

                represented_candidate = represented_parent + delta_grid
                residual_candidate = residual_parent.copy()
                candidate_grid = grid_parent + delta_grid

                min_rep = float(np.min(represented_candidate))
                split_err = float(np.max(np.abs(
                    candidate_grid - represented_candidate - residual_candidate
                )))
                downstream["represented_nonnegative_pass"] = min_rep >= -MASS_TOL
                downstream["split_identity_pass"] = split_err <= MASS_TOL

                full_sat = np.full(GRID, float(a2e.INJECTED), dtype=np.float64)
                cart_capacity = np.asarray(
                    a2e.local_mass(r2, full_sat, pressure_psi, p_ref, hetero_pv),
                    dtype=np.float64,
                )
                cart_cap_tol = max(
                    1e-8,
                    1e-12 * max(float(np.max(cart_capacity)), 1.0),
                )
                cart_excess = float(np.max(candidate_grid - cart_capacity))
                downstream["heterogeneous_cartesian_capacity_pass"] = cart_excess <= cart_cap_tol

                candidate_sat = None
                candidate_mass_err = None
                if downstream["heterogeneous_cartesian_capacity_pass"]:
                    candidate_sg = np.asarray(
                        a2e.invert_local_mass(
                            r2,
                            candidate_grid,
                            pressure_psi,
                            p_ref,
                            hetero_pv,
                        ),
                        dtype=np.float64,
                    )
                    candidate_sat = float(a2e.BACKGROUND) + candidate_sg
                    reconstructed = np.asarray(
                        a2e.local_mass(
                            r2,
                            candidate_sat,
                            pressure_psi,
                            p_ref,
                            hetero_pv,
                        ),
                        dtype=np.float64,
                    )
                    candidate_mass_err = float(np.max(np.abs(
                        reconstructed - candidate_grid
                    )))
                    downstream["heterogeneous_cartesian_inversion_pass"] = (
                        candidate_mass_err <= 1e-8
                        and float(np.min(candidate_sat)) >= BACKGROUND - SAT_TOL
                        and float(np.max(candidate_sat)) <= MAX_SATURATION + SAT_TOL
                    )

                target_total = float(np.sum(grid_parent)) + injected - produced_adjusted
                candidate_total = float(np.sum(candidate_grid))
                cart_source_sink_residual = candidate_total - target_total
                downstream["cartesian_source_sink_closure_pass"] = (
                    abs(cart_source_sink_residual) <= grid_tol
                )

                downstream.update({
                    "CV_max_capacity_excess_kg": prospective_max_capacity_excess,
                    "CV_min_mass_kg": prospective_min_mass,
                    "CV_source_sink_residual_kg": prospective_cv_residual,
                    "CV_to_subsegment_residual_kg": transfer_residual,
                    "subsegment_to_grid_residual_kg": deposit_residual,
                    "minimum_represented_candidate_mass_kg": min_rep,
                    "split_identity_max_abs_error_kg": split_err,
                    "cartesian_max_capacity_excess_kg": cart_excess,
                    "cartesian_capacity_tolerance_kg": cart_cap_tol,
                    "cartesian_cellwise_mass_reconstruction_error_kg": candidate_mass_err,
                    "cartesian_source_sink_residual_kg": cart_source_sink_residual,
                    "candidate_saturation_min": (
                        float(np.min(candidate_sat)) if candidate_sat is not None else None
                    ),
                    "candidate_saturation_max": (
                        float(np.max(candidate_sat)) if candidate_sat is not None else None
                    ),
                })

                required = (
                    "face_flux_projection_feasible",
                    "CV_nonnegative_pass",
                    "CV_capacity_pass",
                    "CV_source_sink_closure_pass",
                    "CV_inversion_pass",
                    "CV_to_subsegment_closure_pass",
                    "subsegment_to_grid_closure_pass",
                    "represented_nonnegative_pass",
                    "split_identity_pass",
                    "heterogeneous_cartesian_capacity_pass",
                    "heterogeneous_cartesian_inversion_pass",
                    "cartesian_source_sink_closure_pass",
                )
                downstream["all_downstream_checks_pass"] = all(
                    bool(downstream[k]) for k in required
                )

                prospective_arrays = {
                    "prospective_adjusted_face_mass_flux_kg_day": adjusted_flux,
                    "prospective_new_CV_mass_kg": prospective_new_mass,
                    "prospective_new_CV_saturation": prospective_sat,
                    "prospective_delta_grid_mass_kg": delta_grid,
                    "prospective_represented_candidate_mass_kg": represented_candidate,
                    "prospective_candidate_grid_mass_kg": candidate_grid,
                }

            except Exception as exc:
                downstream["exception"] = repr(exc)

        if not prospective_feasible:
            classification = (
                "CAPACITY_CONSTRAINED_FACE_FLUX_PROJECTION_INFEASIBLE_AT_NOMINAL_DT_"
                "UNDER_FIXED_INLET_AND_PHYSICAL_FACE_FLUX_ENVELOPE"
            )
        elif downstream["all_downstream_checks_pass"]:
            classification = (
                "CAPACITY_CONSTRAINED_CONSERVATIVE_FACE_FLUX_REPAIR_FEASIBLE_AT_"
                "NOMINAL_DT_WITH_FULL_DOWNSTREAM_PROPAGATION_CLOSURE"
            )
        else:
            classification = (
                "CAPACITY_CONSTRAINED_FACE_FLUX_REPAIR_FEASIBLE_AT_CV_LEVEL_BUT_"
                "ADDITIONAL_DOWNSTREAM_REPAIR_REQUIRED"
            )

        # ------------------------------------------------------------------
        # Design freeze publication.
        # ------------------------------------------------------------------
        stage = "design_freeze_publication"
        out.mkdir(parents=True, exist_ok=False)

        arrays = {
            "nominal_face_mass_flux_kg_day": nominal_face_flux,
            "physical_max_face_mass_flux_kg_day": physical_max_face_flux,
            "prospective_adjusted_face_mass_flux_kg_day": adjusted_flux,
            "face_mass_flux_correction_kg_day": correction,
            "face_flux_lower_required_kg_day": lower_required,
            "face_flux_upper_allowed_kg_day": upper_allowed,
            "face_flux_lower_feasible_kg_day": lower_feasible,
            "face_flux_upper_feasible_kg_day": upper_feasible,
            "face_flux_infeasible_mask": infeasible_mask,
            "prospective_new_CV_mass_kg": prospective_new_mass,
            "prospective_CV_capacity_excess_kg": prospective_capacity_excess,
            "nominal_CV_capacity_excess_kg": nominal_excess,
            "streamline_id": streamline_id,
            "producer_labels": producer_labels,
        }
        arrays.update(prospective_arrays)
        npz_name = f"{OUT_TOKEN}_Prospective_CapacityConstrained_Flux_and_Propagation.npz"
        (out / npz_name).write_bytes(deterministic_npz_bytes(arrays))

        infeasible_rows = []
        if infeasible_count:
            for sl, cv in np.argwhere(infeasible_mask):
                infeasible_rows.append({
                    "streamline_index": int(sl),
                    "streamline_id": int(streamline_id[sl]),
                    "cv_index": int(cv),
                    "incoming_adjusted_flux_kg_day": float(adjusted_flux[sl, cv]),
                    "nominal_outgoing_flux_kg_day": float(nominal_face_flux[sl, cv + 1]),
                    "minimum_required_outgoing_flux_kg_day": float(lower_feasible[sl, cv]),
                    "maximum_physical_outgoing_flux_kg_day": float(upper_feasible[sl, cv]),
                    "old_mass_kg": float(old_cv_mass[sl, cv]),
                    "capacity_kg": float(cv_capacity[sl, cv]),
                })
        (out / f"{OUT_TOKEN}_FaceFlux_Infeasibility_Localization.csv").write_bytes(
            csvb(infeasible_rows)
        )

        design = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "scientific_problem": (
                "accepted parent contains CVs at exact capacity with positive nominal "
                "net component inflow, so unchanged explicit E37A transport has zero "
                "positive admissible timestep"
            ),
            "repair_family": "capacity-constrained conservative one-way face-flux projection",
            "frozen_equation": "M_new[i] = M_old[i] + dt*(F[i]-F[i+1])",
            "capacity_constraint": "0 <= M_new[i] <= C[i]",
            "derived_outflow_lower_bound": "F[i+1] >= F[i] - (C[i]-M_old[i])/dt",
            "derived_outflow_upper_bound": "F[i+1] <= F[i] + M_old[i]/dt",
            "physical_flux_envelope": "0 <= F[i+1] <= Fmax[i+1](S=0.80)",
            "selection_rule": (
                "choose feasible outgoing face flux closest to nominal explicit E37A "
                "flux in a causal forward sweep along each positive-flow streamline"
            ),
            "inlet_component_mass_flux_preserved_exactly": True,
            "injection_rate_reduction_authorized": False,
            "nominal_dt_preserved_in_prospective_test": True,
            "pressure_refresh_required_by_design": False,
            "residual_sidecar_participates_in_flux_projection": False,
            "subsegment_delta_formula_changed": False,
            "Cartesian_mapback_formula_changed": False,
            "heterogeneous_AV4_cartesian_PV_required": True,
            "state_mutation_executed": False,
            "physical_time_advance_executed": False,
            "prospective_feasibility": {
                "face_flux_projection_feasible": prospective_feasible,
                "infeasible_CV_count": infeasible_count,
                "corrected_face_count": corrected_face_count,
                "maximum_abs_flux_correction_kg_day": max_abs_flux_correction,
                "L1_flux_correction_kg_day": l1_flux_correction,
                "produced_mass_nominal_kg": produced_nominal,
                "produced_mass_prospective_kg": produced_adjusted,
                "prospective_CV_max_capacity_excess_kg": prospective_max_capacity_excess,
                "prospective_CV_min_mass_kg": prospective_min_mass,
            },
            "full_downstream_propagation": downstream,
        }

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": classification,
            "source_R29R3R1_summary_sha256": mm[R1_SUMMARY],
            "source_R29R3_scientific_fail_sha256": R29R3_FAIL_SHA256,
            "nominal_dt_days": DT_NOMINAL,
            "nominal_target_day": TARGET_NOMINAL,
            "R1_zero_capacity_dt_confirmed": True,
            "R1_nominal_CV_capacity_violation_count": int(s1["nominal_CV_capacity_violation_count"]),
            "face_flux_projection_feasible": prospective_feasible,
            "face_flux_infeasible_CV_count": infeasible_count,
            "corrected_face_count": corrected_face_count,
            "maximum_abs_flux_correction_kg_day": max_abs_flux_correction,
            "L1_flux_correction_kg_day": l1_flux_correction,
            "injected_mass_kg": injected,
            "produced_mass_nominal_kg": produced_nominal,
            "produced_mass_prospective_kg": produced_adjusted,
            "prospective_CV_component_mass_delta_kg": prospective_cv_delta,
            "prospective_CV_source_sink_residual_kg": prospective_cv_residual,
            "prospective_CV_min_mass_kg": prospective_min_mass,
            "prospective_CV_max_capacity_excess_kg": prospective_max_capacity_excess,
            "downstream_all_checks_pass": downstream["all_downstream_checks_pass"],
            "downstream_exception": downstream["exception"],
            "state_mutation_executed": False,
            "physical_time_advance_executed": False,
            "automatic_dt_reduction_executed": False,
            "pressure_refresh_executed": False,
            "R30_authorized": False,
            "P3_authorized": False,
        }

        execution_ready = (
            prospective_feasible and downstream["all_downstream_checks_pass"]
        )
        decision = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "P2_R6_R29_R3_R3_authorized": bool(execution_ready),
            "P2_R6_R29_R3_R3_name": (
                "Controlled Capacity-Constrained Conservative Face-Flux Transport "
                "Candidate Execution — Nominal dt — No Time Commit"
            ),
            "P2_R6_R29_R3_R3_execution_authorized": bool(execution_ready),
            "P2_R6_R29_R3_R3_candidate_only": bool(execution_ready),
            "P2_R6_R29_R3_R3_must_bind_this_design": True,
            "P2_R6_R29_R3_R3_nominal_dt_days": DT_NOMINAL,
            "P2_R6_R29_R3_R3_target_day": TARGET_NOMINAL,
            "inlet_component_flux_change_authorized": False,
            "nominal_dt_change_authorized": False,
            "capacity_constrained_face_flux_projection_authorized": bool(execution_ready),
            "physical_face_flux_envelope_required": True,
            "subsegment_delta_formula_change_authorized": False,
            "Cartesian_mapback_formula_change_authorized": False,
            "residual_sidecar_mutation_authorized": False,
            "support_growth_authorized": False,
            "pressure_refresh_authorized": False,
            "physical_time_advance_authorized": False,
            "automatic_rerun_authorized": False,
            "R30_authorized": False,
            "P3_authorized": False,
        }

        (out / f"PAD_Stream_{OUT_TOKEN}_Summary.json").write_bytes(jb(summary))
        (out / f"{OUT_TOKEN}_Capacity_Constrained_FaceFlux_Design_Freeze.json").write_bytes(jb(design))
        (out / f"{OUT_TOKEN}_Decision_Contract.json").write_bytes(jb(decision))
        (out / f"{OUT_TOKEN}_Final_Gate_Matrix.csv").write_bytes(csvb(gates))

        rows = []
        for p in sorted(out.iterdir()):
            if p.is_file():
                rows.append({"file": p.name, "sha256": sha(p), "bytes": p.stat().st_size})
        (out / f"{OUT_TOKEN}_Artifact_Manifest.csv").write_bytes(csvb(rows))

        print("=" * 200)
        print(M, "PASS")
        print("Classification                         :", classification)
        print("R1 zero-capacity-dt confirmed          : True")
        print("Face-flux projection feasible          :", prospective_feasible)
        print("Infeasible CV count                    :", infeasible_count)
        print("Corrected face count                   :", corrected_face_count)
        print("Max abs face-flux correction kg/day    :", max_abs_flux_correction)
        print("Nominal / prospective produced mass kg :", produced_nominal, "/", produced_adjusted)
        print("Prospective CV max capacity excess kg  :", prospective_max_capacity_excess)
        print("Prospective CV min mass kg             :", prospective_min_mass)
        print("Full downstream propagation PASS       :", downstream["all_downstream_checks_pass"])
        print("R29-R3-R3 execution authorized         :", execution_ready)
        print("State / time / dt change               : False / False / False")
        print("R30 authorized                         : False")
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
                "R29R3_SCIENTIFIC_FAIL_preserved": True,
                "R29R3R1_audit_preserved": True,
                "state_mutation_executed": False,
                "physical_time_advance_executed": False,
                "automatic_rerun_authorized": False,
                "R30_authorized": False,
                "P3_authorized": False,
                "gates_completed": gates,
            }))
        print("=" * 200)
        print(M, "TECHNICAL / AUTHORITY BLOCK")
        print("Stage    :", stage)
        print("Exception:", repr(exc))
        print("NO STATE MUTATION / TIME ADVANCE / AUTOMATIC RERUN.")
        print("=" * 200)
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
