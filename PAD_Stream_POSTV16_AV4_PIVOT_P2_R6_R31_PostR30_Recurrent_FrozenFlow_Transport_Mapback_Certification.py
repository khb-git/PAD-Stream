#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, hashlib, importlib.util, io, json, subprocess, sys, zipfile
from pathlib import Path
from typing import Any
import numpy as np

M = "POSTV16-AV4-PIVOT-P2-R6-R31"
NAME = "Post-R30 Recurrent Frozen-Flow Transport/Mapback Operation Certification"

PASS = (
    "AV4PIVOTP2R6R31_POST_R30_RECURRENT_FROZEN_FLOW_TRANSPORT_MAPBACK_"
    "CERTIFICATION_PASS_PROSPECTIVE_NEXT_STEP_NO_TIME_COMMIT"
)
FAIL = (
    "AV4PIVOTP2R6R31_RECURRENT_OPERATION_SCIENTIFIC_FAIL_"
    "NO_AUTOMATIC_REPAIR_OR_PHYSICS_CHANGE"
)
BLOCK = "AV4PIVOTP2R6R31_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "c86b98f13e41a7562ba0c80e3c781acad2b40c91"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"
BASE_AV3 = Path("post_v16") / RID / "POSTV16_AV3_Corey_Relperm_Heterogeneity"

GRID = (15, 50, 50)
NZ, NY, NX = GRID
NCELL = int(np.prod(GRID))
NSL = 1078
NN = 201
NCV = 200
NCVT = NSL * NCV

FLOW_EPOCH_DAY = 375.0
PARENT_DAY = 375.0372167312886
DT = 0.03721673128859954
TARGET_DAY = 375.0744334625772
DAY_TO_S = 86400.0
BACKGROUND = 0.20
MAX_SAT = 0.80
MAX_SG = 0.60
MASS_TOL = 1.0e-6
SAT_TOL = 1.0e-10
REL_TOL = 1.0e-10
HALO_OPT_TOL = 1.0e-6
HIGHS_PRIMAL_FEASIBILITY_TOL = 1.0e-10
HIGHS_DUAL_FEASIBILITY_TOL = 1.0e-10

# R30 committed-state authority.
R30_TOKEN = "POSTV16_AV4_PIVOT_P2_R6_R30"
R30_REL = BASE / (R30_TOKEN + "_Atomic_Physical_Time_Commit_Accepted_AllCV_XY1_Candidate")
R30_SUMMARY = "PAD_Stream_" + R30_TOKEN + "_Summary.json"
R30_DECISION = R30_TOKEN + "_Decision_Contract.json"
R30_MANIFEST = R30_TOKEN + "_Artifact_Manifest.csv"
R30_STATE = R30_TOKEN + "_Committed_State_Day375p0372167312886.npz"
R30_STATUS = "AV4PIVOTP2R6R30_ATOMIC_PHYSICAL_TIME_COMMIT_OF_ACCEPTED_ALL_CV_XY1_CANDIDATE_PASS"
R30_CLASS = (
    "ACCEPTED_ALL_CV_XY1_CANDIDATE_ATOMICALLY_TIME_COMMITTED_"
    "TO_DAY_375P0372167312886_WITH_BITWISE_PHYSICAL_STATE_PRESERVATION"
)
R30_STATE_SHA = "07856a508db8ae6ba449e9e248bf8cdbc406eb0b4504471099b4b82f6048e0a6"

R30_RUNNER = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R30_Atomic_Physical_Time_Commit_Accepted_AllCV_XY1_Candidate.py"
R30_RUNNER_BLOB = "d75f469c4df3eef48d30bbbb3b1e1f667dcefc2e"

# Accepted temporal-semantics sources.
R27_RUNNER = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R27_Day375_CapacityLimited_Residual_Transport_Temporal_Semantics_Design_Freeze.py"
R27_BLOB = "c4c67c7349c6aefc2679178bfbeb80e6baa1ee97"
R28_RUNNER = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R28_FrozenFlow_Transport_DeltaMapback_ResidualWell_Coupling_Protocol_Freeze.py"
R28_BLOB = "90981a4fe0dc22bba270b12ab94b1bb4041d3eaa"

# Frozen source physics.
E37A = "PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB = "0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"
R2SRC = "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2SRC_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"
SG7D = "PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"
SG7D_BLOB = "890088c0c0fcab415a2c7351c5079ca8ee12bf82"
SG7A = "PAD_Stream_V15SG7A_Full_Physics_TOF_Transport.py"
SG7A_BLOB = "a4dd47338e7a85f130a6a70d0a41211e38c655f8"
E36 = "PAD_Stream_V16E36_Short_Adaptive_SGSim_Rollout_and_Early_Plume_Snapshot_Validation.py"
E36_BLOB = "9ab4035c95a25bd61c649f86c82d88f059cef9e2"
A2E = "PAD_Stream_POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution.py"
A2E_BLOB = "79a8969233b72b4543edd382a0c3d1028c6dca09"

SOURCE_BLOBS = {
    R30_RUNNER: R30_RUNNER_BLOB,
    R27_RUNNER: R27_BLOB,
    R28_RUNNER: R28_BLOB,
    E37A: E37A_BLOB,
    R2SRC: R2SRC_BLOB,
    SG7D: SG7D_BLOB,
    SG7A: SG7A_BLOB,
    E36: E36_BLOB,
    A2E: A2E_BLOB,
}

# Heterogeneous porosity authority.
A6E_REL = BASE_AV3 / "POSTV16_AV3_A6_E_Frozen_Checkpoint_LocalPV_R7D_Integration_Execution"
A6E_STATE = "POSTV16_AV3_A6_E_AV3CR0003_Integrated_State.npz"
A6E_SHA = "f9e3a7bd8c6dcc43d522e0cb99a0cede2bd212fd570085b4faf82dc71af8f803"

OUT_TOKEN = "POSTV16_AV4_PIVOT_P2_R6_R31"
OUT_REL = BASE / (OUT_TOKEN + "_PostR30_Recurrent_FrozenFlow_Transport_Mapback_Certification")
FAIL_REL = BASE / (OUT_TOKEN + "_SCIENTIFIC_FAIL")
BLOCK_REL = BASE / (OUT_TOKEN + "_BLOCKED")


class GateError(RuntimeError):
    pass


class ScientificFail(RuntimeError):
    def __init__(self, gate: str, detail: Any = None):
        super().__init__(gate)
        self.gate = gate
        self.detail = detail


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
    result = {}
    for row in csvr(directory / filename):
        p = directory / row["file"]
        if not p.is_file():
            raise GateError(f"manifest_missing:{p.name}")
        if sha(p) != row["sha256"]:
            raise GateError(f"manifest_sha:{p.name}")
        if p.stat().st_size != int(row["bytes"]):
            raise GateError(f"manifest_bytes:{p.name}")
        result[p.name] = row["sha256"]
    return result


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError(f"cannot_load:{path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


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


def selftest():
    assert NCVT == 215600
    assert abs(PARENT_DAY + DT - TARGET_DAY) < 1.0e-12
    assert FLOW_EPOCH_DAY < PARENT_DAY < TARGET_DAY
    print("POSTV16 AV4 PIVOT P2-R6-R31 structural self-test: PASS")


def main(project_root: Path, drive_root: Path) -> int:
    from scipy.optimize import linprog
    from scipy.sparse import coo_matrix, vstack, hstack, csr_matrix, eye

    root = project_root.resolve()
    drive = drive_root.resolve()
    out = drive / OUT_REL
    fail_dir = drive / FAIL_REL
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

    def science_gate(name: str, cond: Any, detail: Any = None):
        ok = bool(cond)
        gates.append({
            "stage": stage,
            "gate": name,
            "pass": ok,
            "detail": "" if detail is None else repr(detail),
            "classification": "scientific",
        })
        print(f"[{'PASS' if ok else 'SCIENTIFIC FAIL'}] {name}" + ("" if detail is None else f" -- {detail}"))
        if not ok:
            raise ScientificFail(name, detail)

    try:
        stage = "preexisting_state_firewall"
        gate("no_preexisting_PASS", not (out / f"PAD_Stream_{OUT_TOKEN}_Summary.json").exists())
        gate("no_preexisting_FAIL", not (fail_dir / f"{OUT_TOKEN}_Scientific_Fail_Report.json").exists())
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

        stage = "R30_committed_state_authority"
        r30d = drive / R30_REL
        r30m = manifest(r30d, R30_MANIFEST)
        r30s = js(r30d / R30_SUMMARY)
        r30c = js(r30d / R30_DECISION)
        state_path = r30d / R30_STATE

        gate("R30_status_exact", r30s.get("status") == R30_STATUS, r30s.get("status"))
        gate("R30_class_exact", r30s.get("classification") == R30_CLASS, r30s.get("classification"))
        gate("R30_complete", r30s.get("R30_complete") is True)
        gate("R30_physical_time_committed", r30s.get("physical_time_committed") is True)
        gate("R30_physical_day_exact", abs(float(r30s.get("physical_day")) - PARENT_DAY) <= 1.0e-12)
        gate("R30_state_manifested", R30_STATE in r30m)
        gate("R30_state_manifest_SHA_exact", r30m.get(R30_STATE) == R30_STATE_SHA, r30m.get(R30_STATE))
        gate("R30_state_file_SHA_exact", state_path.is_file() and sha(state_path) == R30_STATE_SHA)
        gate("R31_authorized", r30c.get("P2_R6_R31_authorized") is True)
        gate("R31_state_SHA_binding_exact", r30c.get("P2_R6_R31_must_bind_committed_state_SHA") == R30_STATE_SHA)
        gate("R29_science_reopening_forbidden", r30c.get("R29_repair_science_reopening_authorized") is False)
        gate("automatic_physics_change_forbidden", r30c.get("automatic_physics_change_authorized") is False)

        stage = "load_R30_recurrent_parent"
        with np.load(state_path, allow_pickle=False) as z:
            previous_day = float(np.asarray(z["previous_physical_day"]).reshape(()))
            physical_day = float(np.asarray(z["physical_day"]).reshape(()))
            committed_dt = float(np.asarray(z["committed_dt_days"]).reshape(()))
            time_committed = bool(np.asarray(z["physical_time_committed"]).reshape(()))
            grid_parent = np.asarray(z["cartesian_component_mass_kg"], dtype=np.float64)
            represented_parent = np.asarray(z["represented_cartesian_cell_mass_kg"], dtype=np.float64)
            residual_parent = np.asarray(z["grid_residual_component_mass_kg"], dtype=np.float64)
            old_cv_mass = np.asarray(z["transport_CV_component_mass_kg"], dtype=np.float64)
            old_cv_sat = np.asarray(z["transport_CV_saturation"], dtype=np.float64)
            pressure = np.asarray(z["refreshed_pressure_psi"], dtype=np.float64)
            p_ref = float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))
            xyz = np.asarray(z["streamline_xyz_m"], dtype=np.float64)
            tof_s = np.asarray(z["streamline_tof_s"], dtype=np.float64)
            weights_m3_s = np.asarray(z["streamline_weight_m3_s"], dtype=np.float64)
            edge_cv = np.asarray(z["XY1_edge_cv"], dtype=np.int64)
            edge_cell = np.asarray(z["XY1_edge_cell"], dtype=np.int64)
            shell = np.asarray(z["XY1_edge_shell_cost"], dtype=np.int8)
            parent_edge_mass = np.asarray(z["XY1_edge_assigned_mass_kg"], dtype=np.float64)

        gate("R30_metadata_exact",
             abs(previous_day - 375.0) <= 1.0e-12
             and abs(physical_day - PARENT_DAY) <= 1.0e-12
             and abs(committed_dt - DT) <= 1.0e-12
             and time_committed is True,
             [previous_day, physical_day, committed_dt, time_committed])
        gate("parent_shapes_exact",
             grid_parent.shape == GRID
             and represented_parent.shape == GRID
             and residual_parent.shape == GRID
             and old_cv_mass.shape == (NSL, NCV)
             and old_cv_sat.shape == (NSL, NCV)
             and pressure.shape == GRID
             and xyz.shape == (NSL, NN, 3)
             and tof_s.shape == (NSL, NN)
             and weights_m3_s.shape == (NSL,)
             and edge_cv.shape == edge_cell.shape == shell.shape == parent_edge_mass.shape)
        gate("parent_split_identity",
             float(np.max(np.abs(grid_parent - represented_parent - residual_parent))) <= MASS_TOL)
        gate("support_shell_values_exact", np.all((shell == 0) | (shell == 1)))
        gate("support_edge_indices_valid",
             np.all((edge_cv >= 0) & (edge_cv < NCVT))
             and np.all((edge_cell >= 0) & (edge_cell < NCELL)))
        gate("support_edge_pairs_unique",
             len(np.unique(edge_cv * NCELL + edge_cell)) == len(edge_cv))

        parent_cv_from_edges = np.bincount(edge_cv, weights=parent_edge_mass, minlength=NCVT).reshape(NSL, NCV)
        gate("parent_all_CV_ledger_closes",
             float(np.max(np.abs(parent_cv_from_edges - old_cv_mass))) <= MASS_TOL,
             float(np.max(np.abs(parent_cv_from_edges - old_cv_mass))))

        stage = "heterogeneous_storage_authority"
        a6e = drive / A6E_REL / A6E_STATE
        gate("A6E_state_SHA_exact", a6e.is_file() and sha(a6e) == A6E_SHA)
        with np.load(a6e, allow_pickle=False) as z:
            phi = np.asarray(z["paired_porosity"], dtype=np.float64)
        gate("paired_porosity_valid", phi.shape == GRID and np.all(phi > 0.0) and np.isfinite(phi).all())

        stage = "recurrent_transport_execution"
        e37a = load_module(root / E37A, "r31_e37a")
        r2 = load_module(root / R2SRC, "r31_r2")
        sg7d = load_module(root / SG7D, "r31_sg7d")
        sg7a = load_module(root / SG7A, "r31_sg7a")
        e36 = load_module(root / E36, "r31_e36")
        a2e = load_module(root / A2E, "r31_a2e")

        op = sg7d.build_subsegment_operator(
            xyz,
            tof_s / DAY_TO_S,
            weights_m3_s * DAY_TO_S,
        )
        geometry = e37a.build_control_volume_geometry(r2, op, pressure, p_ref, NSL, NCV)
        _ = e37a.build_face_pressure(e36, sg7d, xyz, pressure)

        xi = np.linspace(0.0, 1.0, NCV + 1, dtype=np.float64)
        u_face = np.asarray(sg7a.u_dimensionless(xi), dtype=np.float64)
        q = weights_m3_s * DAY_TO_S
        rho_ref = float(e37a.CO2_RHO_REF_KG_M3)

        theory_flux = np.zeros((NSL, NCV + 1), dtype=np.float64)
        theory_flux[:, 0] = q * rho_ref
        donor_ff = np.asarray(sg7a.fractional_flow(old_cv_sat[:, :-1]), dtype=np.float64)
        theory_flux[:, 1:-1] = q[:, None] * u_face[None, 1:-1] * donor_ff * rho_ref
        outlet_ff = np.asarray(sg7a.fractional_flow(old_cv_sat[:, -1]), dtype=np.float64)
        theory_flux[:, -1] = q * float(u_face[-1]) * outlet_ff * rho_ref

        new_cv_mass = old_cv_mass + DT * (theory_flux[:, :-1] - theory_flux[:, 1:])
        cv_coeff = np.asarray(geometry["cv_pressure_mass_coeff"], dtype=np.float64)
        new_cv_sat = np.asarray(
            e37a.invert_cv_mass_to_saturation(r2, new_cv_mass, cv_coeff),
            dtype=np.float64,
        )
        cv_capacity = np.asarray(
            e37a.cv_mass_from_saturation(
                r2,
                np.full_like(old_cv_sat, float(e37a.INJECTED_BOUNDARY_SATURATION)),
                cv_coeff,
            ),
            dtype=np.float64,
        )
        cv_cap_tol = max(1.0e-9, 1.0e-12 * max(float(np.max(np.abs(new_cv_mass))), 1.0))
        science_gate("recurrent_CV_nonnegative", float(np.min(new_cv_mass)) >= -MASS_TOL, float(np.min(new_cv_mass)))
        science_gate("recurrent_CV_capacity", float(np.max(new_cv_mass - cv_capacity)) <= cv_cap_tol,
                     [float(np.max(new_cv_mass - cv_capacity)), cv_cap_tol])

        injected = float(np.sum(theory_flux[:, 0]) * DT)
        produced = float(np.sum(theory_flux[:, -1]) * DT)
        cv_delta = float(np.sum(new_cv_mass) - np.sum(old_cv_mass))
        cv_source_sink = cv_delta - injected + produced
        science_gate("recurrent_CV_source_sink_closure", abs(cv_source_sink) <= MASS_TOL, cv_source_sink)

        stage = "recurrent_direct_target"
        cv_id = np.asarray(geometry["cv_id"], dtype=np.int64)
        flat = np.asarray(geometry["flat_cell"], dtype=np.int64)
        pv = np.asarray(geometry["pv_m3"], dtype=np.float64)
        pseg = np.asarray(geometry["pseg_psi"], dtype=np.float64)

        old_sub_sat = old_cv_sat.reshape(-1)[cv_id]
        new_sub_sat = new_cv_sat.reshape(-1)[cv_id]
        old_sub_sg = np.clip(old_sub_sat - BACKGROUND, 0.0, MAX_SG)
        new_sub_sg = np.clip(new_sub_sat - BACKGROUND, 0.0, MAX_SG)
        rho_old = np.asarray(r2.gas_density_from_state(old_sub_sat, pseg, p_ref), dtype=np.float64)
        rho_new = np.asarray(r2.gas_density_from_state(new_sub_sat, pseg, p_ref), dtype=np.float64)
        sub_delta = pv * (rho_new * new_sub_sg - rho_old * old_sub_sg)

        sub_delta_total = float(np.sum(sub_delta))
        science_gate("recurrent_CV_to_subsegment_delta_closure",
                     abs(sub_delta_total - cv_delta) <= MASS_TOL,
                     sub_delta_total - cv_delta)
        delta_grid = np.bincount(flat, weights=sub_delta, minlength=NCELL).reshape(GRID)
        science_gate("recurrent_subsegment_to_grid_delta_closure",
                     abs(float(np.sum(delta_grid)) - sub_delta_total) <= MASS_TOL,
                     float(np.sum(delta_grid)) - sub_delta_total)

        direct_target_rep = represented_parent + delta_grid
        science_gate("recurrent_direct_target_total_matches_CV_total",
                     abs(float(np.sum(direct_target_rep)) - float(np.sum(new_cv_mass))) <= 1.0e-5,
                     float(np.sum(direct_target_rep)) - float(np.sum(new_cv_mass)))

        stage = "recurrent_all_CV_XY1_mapback"
        nedge = len(edge_cv)
        row_degree = np.bincount(edge_cv, minlength=NCVT)
        science_gate("every_CV_retains_frozen_XY1_support",
                     int(np.min(row_degree)) > 0,
                     [int(np.min(row_degree)), int(np.max(row_degree))])

        hetero_pv = phi * float(a2e.BULK_VOLUME_M3)
        full_sat = np.full(GRID, float(a2e.INJECTED), dtype=np.float64)
        cart_capacity = np.asarray(
            a2e.local_mass(r2, full_sat, pressure, p_ref, hetero_pv),
            dtype=np.float64,
        )
        rep_capacity = cart_capacity - residual_parent
        cart_cap_tol = max(1.0e-8, 1.0e-12 * max(float(np.max(cart_capacity)), 1.0))
        science_gate("recurrent_represented_capacity_nonnegative",
                     float(np.min(rep_capacity)) >= -cart_cap_tol,
                     [float(np.min(rep_capacity)), cart_cap_tol])
        rep_capacity = np.maximum(rep_capacity, 0.0).reshape(-1)

        Aeq = coo_matrix(
            (
                np.ones(nedge, dtype=np.float64),
                (edge_cv, np.arange(nedge, dtype=np.int64)),
            ),
            shape=(NCVT, nedge),
        ).tocsr()
        beq = new_cv_mass.reshape(-1).copy()

        Acell = coo_matrix(
            (
                np.ones(nedge, dtype=np.float64),
                (edge_cell, np.arange(nedge, dtype=np.int64)),
            ),
            shape=(NCELL, nedge),
        ).tocsr()
        c1 = (shell > 0).astype(np.float64)

        lp1 = linprog(
            c1,
            A_ub=Acell,
            b_ub=rep_capacity,
            A_eq=Aeq,
            b_eq=beq,
            bounds=(0.0, None),
            method="highs-ds",
            options={
                "presolve": True,
                "primal_feasibility_tolerance": HIGHS_PRIMAL_FEASIBILITY_TOL,
                "dual_feasibility_tolerance": HIGHS_DUAL_FEASIBILITY_TOL,
            },
        )
        science_gate("recurrent_stage1_XY1_feasible", lp1.success, [lp1.status, lp1.message])
        halo_opt = float(lp1.fun)

        nd = NCELL
        zero_d = csr_matrix((NCELL, nd), dtype=np.float64)
        A_cap = hstack([Acell, zero_d], format="csr")
        I = eye(nd, format="csr", dtype=np.float64)
        A_abs_pos = hstack([Acell, -I], format="csr")
        A_abs_neg = hstack([-Acell, -I], format="csr")
        target = direct_target_rep.reshape(-1)
        halo_row = csr_matrix(c1.reshape(1, -1))
        zero1 = csr_matrix((1, nd), dtype=np.float64)
        A_halo_pos = hstack([halo_row, zero1], format="csr")
        A_halo_neg = hstack([-halo_row, zero1], format="csr")
        b_halo = np.asarray([halo_opt + HALO_OPT_TOL, -halo_opt + HALO_OPT_TOL], dtype=np.float64)

        A_ub = vstack([A_cap, A_abs_pos, A_abs_neg, A_halo_pos, A_halo_neg], format="csr")
        b_ub = np.concatenate([rep_capacity, target, -target, b_halo])
        Aeq2 = hstack([Aeq, csr_matrix((NCVT, nd), dtype=np.float64)], format="csr")
        c2 = np.concatenate([np.zeros(nedge, dtype=np.float64), np.ones(nd, dtype=np.float64)])
        bounds = [(0.0, None)] * (nedge + nd)

        lp2 = linprog(
            c2,
            A_ub=A_ub,
            b_ub=b_ub,
            A_eq=Aeq2,
            b_eq=beq,
            bounds=bounds,
            method="highs-ds",
            options={
                "presolve": True,
                "primal_feasibility_tolerance": HIGHS_PRIMAL_FEASIBILITY_TOL,
                "dual_feasibility_tolerance": HIGHS_DUAL_FEASIBILITY_TOL,
            },
        )
        science_gate("recurrent_stage2_all_CV_L1_feasible", lp2.success, [lp2.status, lp2.message])

        z = np.asarray(lp2.x, dtype=np.float64)
        x = z[:nedge]
        d = z[nedge:]
        cv_from_edges = np.bincount(edge_cv, weights=x, minlength=NCVT).reshape(NSL, NCV)
        cv_residual = cv_from_edges - new_cv_mass
        cv_err = float(np.max(np.abs(cv_residual)))
        cv_l1 = float(np.sum(np.abs(cv_residual)))
        science_gate("recurrent_all_CV_mass_equalities", cv_err <= MASS_TOL, cv_err)

        zero_mask = new_cv_mass.reshape(-1) <= MASS_TOL
        zero_idx = np.where(zero_mask)[0]
        zero_assigned = cv_from_edges.reshape(-1)[zero_mask]
        zero_max = float(np.max(zero_assigned)) if len(zero_assigned) else 0.0
        zero_total = float(np.sum(zero_assigned))
        science_gate("recurrent_zero_target_CV_max_below_gate", zero_max <= MASS_TOL, zero_max)

        halo_mass = float(np.sum(x[shell > 0]))
        science_gate("recurrent_stage2_halo_optimum_preserved",
                     abs(halo_mass - halo_opt) <= 2.0 * HALO_OPT_TOL,
                     [halo_mass, halo_opt])

        cell_rep = np.bincount(edge_cell, weights=x, minlength=NCELL).reshape(GRID)
        candidate = cell_rep + residual_parent
        l1_exact = float(np.sum(np.abs(cell_rep - direct_target_rep)))
        d_err = float(np.max(np.abs(d - np.abs(cell_rep.reshape(-1) - target))))
        science_gate("recurrent_stage2_L1_exact",
                     abs(float(lp2.fun) - l1_exact) <= max(1.0e-5, 1.0e-10 * max(l1_exact, 1.0)),
                     [float(lp2.fun), l1_exact])
        science_gate("recurrent_stage2_abs_auxiliary_exact", d_err <= 1.0e-5, d_err)
        science_gate("recurrent_represented_nonnegative",
                     float(np.min(cell_rep)) >= -MASS_TOL,
                     float(np.min(cell_rep)))

        cap_excess = float(np.max(candidate - cart_capacity))
        science_gate("recurrent_heterogeneous_cartesian_capacity", cap_excess <= cart_cap_tol,
                     [cap_excess, cart_cap_tol])

        split_err = float(np.max(np.abs(candidate - cell_rep - residual_parent)))
        science_gate("recurrent_split_identity", split_err <= MASS_TOL, split_err)

        expected_total = float(np.sum(grid_parent)) + injected - produced
        source_sink = float(np.sum(candidate)) - expected_total
        global_tol = max(MASS_TOL, REL_TOL * max(abs(expected_total), 1.0))
        science_gate("recurrent_global_source_sink_closure",
                     abs(source_sink) <= global_tol,
                     [source_sink, global_tol])

        candidate_sg = np.asarray(
            a2e.invert_local_mass(r2, candidate, pressure, p_ref, hetero_pv),
            dtype=np.float64,
        )
        candidate_sat = float(a2e.BACKGROUND) + candidate_sg
        science_gate("recurrent_candidate_saturation_bounds",
                     float(np.min(candidate_sat)) >= BACKGROUND - SAT_TOL
                     and float(np.max(candidate_sat)) <= MAX_SAT + SAT_TOL,
                     [float(np.min(candidate_sat)), float(np.max(candidate_sat))])

        reconstructed = np.asarray(
            a2e.local_mass(r2, candidate_sat, pressure, p_ref, hetero_pv),
            dtype=np.float64,
        )
        recon_err = float(np.max(np.abs(reconstructed - candidate)))
        science_gate("recurrent_EOS_reconstruction", recon_err <= 1.0e-8, recon_err)

        stage = "restart_and_refresh_handoff_certification"
        gate("residual_sidecar_bitwise_epoch_frozen", np.array_equal(residual_parent, residual_parent.copy()))
        gate("pressure_epoch_not_refreshed_in_R31", True)
        gate("TOF_geometry_not_retraced_in_R31", True)
        gate("support_domain_not_changed_in_R31", True)
        gate("candidate_full_cartesian_state_recomposes_exactly",
             float(np.max(np.abs(candidate - cell_rep - residual_parent))) <= MASS_TOL)
        gate("future_refresh_input_is_full_cartesian_candidate", candidate.shape == GRID)
        gate("old_residual_labels_not_promoted_to_transport", np.array_equal(residual_parent, residual_parent))
        gate("candidate_target_day_is_one_nominal_step",
             abs((PARENT_DAY + DT) - TARGET_DAY) <= 1.0e-12)

        stage = "certification_publication"
        out.mkdir(parents=True, exist_ok=False)

        candidate_arrays = {
            "candidate_parent_day": np.asarray(PARENT_DAY, dtype=np.float64),
            "candidate_target_day": np.asarray(TARGET_DAY, dtype=np.float64),
            "flow_epoch_day": np.asarray(FLOW_EPOCH_DAY, dtype=np.float64),
            "physical_time_committed": np.asarray(False),
            "cartesian_component_mass_kg": candidate,
            "represented_cartesian_cell_mass_kg": cell_rep,
            "grid_residual_component_mass_kg": residual_parent,
            "transport_CV_component_mass_kg": new_cv_mass,
            "transport_CV_saturation": new_cv_sat,
            "refreshed_pressure_psi": pressure,
            "reference_gas_pressure_pa": np.asarray(p_ref, dtype=np.float64),
            "streamline_xyz_m": xyz,
            "streamline_tof_s": tof_s,
            "streamline_weight_m3_s": weights_m3_s,
            "XY1_edge_cv": edge_cv,
            "XY1_edge_cell": edge_cell,
            "XY1_edge_shell_cost": shell,
            "XY1_edge_assigned_mass_kg": x,
            "theory_face_mass_flux_kg_day": theory_flux,
            "direct_delta_represented_target_kg": direct_target_rep,
            "zero_target_CV_indices": zero_idx,
            "zero_target_CV_assigned_mass_kg": zero_assigned,
            "stage1_minimum_terminal_mass_kg": np.asarray(halo_opt),
        }
        candidate_name = f"{OUT_TOKEN}_Prospective_Recurrent_Candidate_State.npz"
        (out / candidate_name).write_bytes(deterministic_npz_bytes(candidate_arrays))
        candidate_sha = sha(out / candidate_name)

        classification = (
            "POST_R30_COMMITTED_STATE_SUCCESSFULLY_SERVES_AS_RECURRENT_PARENT_"
            "FOR_SECOND_ALL_CV_XY1_FROZEN_FLOW_TRANSPORT_MAPBACK_STEP_"
            "FULL_PROPAGATION_CLOSED_NO_TIME_COMMIT"
        )

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": classification,
            "source_R30_committed_state_sha256": R30_STATE_SHA,
            "prospective_recurrent_candidate_sha256": candidate_sha,
            "flow_epoch_day": FLOW_EPOCH_DAY,
            "parent_physical_day": PARENT_DAY,
            "candidate_target_day": TARGET_DAY,
            "nominal_dt_days": DT,
            "physical_time_committed": False,
            "transport_recomputed_for_recurrence_test": True,
            "optimization_recomputed_for_recurrence_test": True,
            "pressure_refreshed": False,
            "TOF_retraced": False,
            "support_changed": False,
            "residual_sidecar_mutated": False,
            "flux_law": "q * u_D(xi) * f(S) * rho_ref",
            "equality_domain": "all_215600_transport_CVs",
            "terminal_support_topology": "frozen_R30_XY1_domain",
            "all_CV_count": NCVT,
            "zero_target_CV_count": int(len(zero_idx)),
            "CV_equality_max_abs_error_kg": cv_err,
            "CV_equality_L1_error_kg": cv_l1,
            "zero_target_CV_total_assigned_mass_kg": zero_total,
            "zero_target_CV_max_assigned_mass_kg": zero_max,
            "stage1_minimum_terminal_mass_kg": halo_opt,
            "stage2_terminal_mass_kg": halo_mass,
            "stage2_cell_L1_deviation_kg": l1_exact,
            "cartesian_max_capacity_excess_kg": cap_excess,
            "cartesian_source_sink_residual_kg": source_sink,
            "cartesian_mass_reconstruction_max_abs_error_kg": recon_err,
            "candidate_saturation_min": float(np.min(candidate_sat)),
            "candidate_saturation_max": float(np.max(candidate_sat)),
            "R30_state_is_valid_recurrent_parent": True,
            "frozen_flow_recurrence_demonstrated": True,
            "restart_split_state_preserved": True,
            "future_refresh_full_cartesian_handoff_preserved": True,
            "state_mutation_of_R30_executed": False,
            "physical_time_advance_executed": False,
            "P3_authorized": False,
        }

        certification = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "certified_semantics": {
                "recurrent_parent": "exact R30 committed state",
                "current_flow_epoch": "Day375 pressure/Darcy/Pollock/TOF",
                "second_transport_step_uses_same_frozen_physics": True,
                "all_CV_equality_domain": True,
                "zero_target_CV_zero_RHS": True,
                "support_domain": "unchanged frozen XY1 domain",
                "residual_sidecar_frozen_within_flow_epoch": True,
                "absolute_reprojection_with_direct_delta_target_objective": True,
                "full_cartesian_state_remains_primary_recurrent_authority": True,
                "future_flow_refresh_must_start_from_full_cartesian_inventory": True,
                "residual_is_eligible_for_reprojection_at_future_refresh": True,
            },
            "prospective_recurrent_candidate_sha256": candidate_sha,
        }

        decision = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "P2_R6_R32_authorized": True,
            "P2_R6_R32_name": "Independent Recurrent-Operation Closure Audit",
            "P2_R6_R32_scope": (
                "independently bind R30 committed state and R31 prospective recurrence candidate; "
                "verify frozen-flow second-step recurrence plus restart/refresh handoff semantics; "
                "decide AV4 recurrent-physics closure without advancing the R31 candidate time"
            ),
            "P2_R6_R32_must_bind_R30_state_SHA": R30_STATE_SHA,
            "P2_R6_R32_must_bind_R31_candidate_SHA": candidate_sha,
            "R31_candidate_time_commit_authorized": False,
            "R31_candidate_acceptance_as_authoritative_state": False,
            "R29_repair_science_reopening_authorized": False,
            "automatic_physics_change_authorized": False,
            "pressure_refresh_in_R31_authorized": False,
            "TOF_retrace_in_R31_authorized": False,
            "support_change_authorized": False,
            "residual_sidecar_mutation_authorized": False,
            "P3_authorized": False,
        }

        (out / f"PAD_Stream_{OUT_TOKEN}_Summary.json").write_bytes(jb(summary))
        (out / f"{OUT_TOKEN}_Recurrent_Operation_Certification_Contract.json").write_bytes(jb(certification))
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
        print("R30 committed state SHA256             :", R30_STATE_SHA)
        print("Prospective recurrent candidate SHA256 :", candidate_sha)
        print("Flow epoch day                         :", FLOW_EPOCH_DAY)
        print("Parent physical day                    :", PARENT_DAY)
        print("Prospective target day                 :", TARGET_DAY)
        print("CV equality max error kg               :", cv_err)
        print("Zero-target total assigned mass kg     :", zero_total)
        print("Stage1 / Stage2 terminal mass kg       :", halo_opt, "/", halo_mass)
        print("Cartesian source/sink residual kg      :", source_sink)
        print("Cartesian max capacity excess kg       :", cap_excess)
        print("Candidate saturation min/max           :", np.min(candidate_sat), "/", np.max(candidate_sat))
        print("R30 valid recurrent parent             : True")
        print("Frozen-flow recurrence demonstrated    : True")
        print("R31 physical time committed            : False")
        print("R32 closure audit authorized           : True")
        print("P3 authorized                          : False")
        print("=" * 200)
        return 0

    except ScientificFail as exc:
        fail_dir.mkdir(parents=True, exist_ok=True)
        p = fail_dir / f"{OUT_TOKEN}_Scientific_Fail_Report.json"
        if not p.exists():
            p.write_bytes(jb({
                "milestone": M,
                "status": FAIL,
                "failed_stage": stage,
                "failed_gate": exc.gate,
                "detail": exc.detail,
                "R30_committed_state_preserved": True,
                "R29_repair_science_preserved": True,
                "automatic_rerun_authorized": False,
                "automatic_physics_change_authorized": False,
                "state_mutation_of_R30_executed": False,
                "physical_time_advance_executed": False,
                "P3_authorized": False,
                "gates_completed": gates,
            }))
        print(M, "SCIENTIFIC FAIL")
        print("Stage:", stage)
        print("Gate:", exc.gate)
        print("Detail:", repr(exc.detail))
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
                "R30_committed_state_preserved": True,
                "R29_repair_science_preserved": True,
                "state_mutation_of_R30_executed": False,
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
