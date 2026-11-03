#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, hashlib, importlib.util, io, json, subprocess, sys, zipfile
from pathlib import Path
from typing import Any
import numpy as np

M = "POSTV16-AV4-PIVOT-P2-R6-R29-R3-R2-R1-R1-R1-R2-R1-R1-R1-R1-R1"
NAME = "Zero-Target CV Equality-Domain Repair Feasibility + Full-Propagation Audit"

PASS = "AV4PIVOTP2R6R29R3R2R1R1R1R2R1R1R1R1R1_ZERO_TARGET_CV_EQUALITY_DOMAIN_REPAIR_FEASIBILITY_AND_FULL_PROPAGATION_AUDIT_PASS_NO_STATE_MUTATION"
BLOCK = "AV4PIVOTP2R6R29R3R2R1R1R1R2R1R1R1R1R1_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "b1fbea043e2b52a18b2e9073fb15ec60c2648d43"

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

DT = 0.03721673128859954
TARGET_DAY = 375.0372167312886
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

# Published-but-preformal parent runners. Their wrappers aborted before formal execution.
PARENT_R1_RUNNER = (
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_R1_R1_R1_R2_R1_"
    "Technical_Closure_TightHiGHS_CVEquality_and_Repair_Design_Freeze.py"
)
PARENT_R1_BLOB = "069e78a10c615261da71a1e530f03d864f269567"

PARENT_R1R1_RUNNER = (
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_R1_R1_R1_R2_R1_R1_"
    "Lost_BLOCK_Artifact_Recovery_and_TightHiGHS_Design_Freeze.py"
)
PARENT_R1R1_BLOB = "50c27eaf6617639c93ba16143cb053029c0bd596"

# Original formal design-freeze runner that reached CV_mass_equalities and BLOCKed.
BLOCKED_DESIGN_RUNNER = (
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_R1_R1_R1_R2_"
    "Comprehensive_TheoryFlux_XY1_TerminalSupport_Mapback_Repair_Design_Freeze.py"
)
BLOCKED_DESIGN_BLOB = "01465a1f55d31c0b6543264627d075da14f60154"

# Foundational accepted parent state.
R25_REL = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R25_R3_"
    "Controlled_Day375_CapacityLimited_ExactSupport_SplitState_"
    "Reprojection_Execution_Stage2_PresolveOff"
)
R25_STATE = "POSTV16_AV4_PIVOT_P2_R6_R25_R3_CapacityLimited_SplitState_Day375.npz"
R25_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R25_R3_Artifact_Manifest.csv"
R25_SHA = "9893e2476bce1d46213cdd1304e60ad93b49ea285e084d06743a2ffab25f721f"

A6E_REL = BASE_AV3 / "POSTV16_AV3_A6_E_Frozen_Checkpoint_LocalPV_R7D_Integration_Execution"
A6E_STATE = "POSTV16_AV3_A6_E_AV3CR0003_Integrated_State.npz"
A6E_SHA = "f9e3a7bd8c6dcc43d522e0cb99a0cede2bd212fd570085b4faf82dc71af8f803"

# Frozen source code authorities used to reconstruct the theory transport candidate.
R25_RUNNER = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R25_R3_Controlled_CapacityLimited_Reprojection_Stage2_PresolveOff.py"
R25_RUNNER_BLOB = "65cab626419137b191f2c53a4c543d9805ccf68d"
E37A = "PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB = "0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"
R2SRC = "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2SRC_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"
A2E = "PAD_Stream_POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution.py"
A2E_BLOB = "79a8969233b72b4543edd382a0c3d1028c6dca09"
SG7D = "PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"
SG7D_BLOB = "890088c0c0fcab415a2c7351c5079ca8ee12bf82"
SG7A = "PAD_Stream_V15SG7A_Full_Physics_TOF_Transport.py"
SG7A_BLOB = "a4dd47338e7a85f130a6a70d0a41211e38c655f8"
E36 = "PAD_Stream_V16E36_Short_Adaptive_SGSim_Rollout_and_Early_Plume_Snapshot_Validation.py"
E36_BLOB = "9ab4035c95a25bd61c649f86c82d88f059cef9e2"

PARENT_BLOCK_TOKEN = "POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_R1_R1_R1_R2_R1_R1_R1"
PARENT_BLOCK_REL = BASE / (PARENT_BLOCK_TOKEN + "_BLOCKED")
PARENT_BLOCK_FILE = PARENT_BLOCK_TOKEN + "_Blocked_Report.json"
PARENT_BLOCK_STATUS = "AV4PIVOTP2R6R29R3R2R1R1R1R2R1R1R1_TECHNICAL_OR_AUTHORITY_BLOCK"
PARENT_BLOCK_STAGE = "comprehensive_design_gates"
PARENT_BLOCK_EXCEPTION = "GateError('tight_CV_mass_equalities')"
PARENT_RUNNER = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_R1_R1_R1_R2_R1_R1_R1_Foundational_Authority_Reconstruction_TightHiGHS_Design_Freeze.py"
PARENT_RUNNER_BLOB = "e67b5e857f909269b7978bf1b3036fe548987a41"

CURRENT_PARENT_RUNNER = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_R1_R1_R1_R2_R1_R1_R1_R1_CVEquality_Residual_Localization_and_ScaledSolver_Audit.py"
CURRENT_PARENT_RUNNER_BLOB = "c6926369b8c463c908fe3328b5c7ca285bb2a7eb"

SOURCE_BLOBS = {
    CURRENT_PARENT_RUNNER: CURRENT_PARENT_RUNNER_BLOB,
    PARENT_RUNNER: PARENT_RUNNER_BLOB,
    PARENT_R1_RUNNER: PARENT_R1_BLOB,
    PARENT_R1R1_RUNNER: PARENT_R1R1_BLOB,
    BLOCKED_DESIGN_RUNNER: BLOCKED_DESIGN_BLOB,
    R25_RUNNER: R25_RUNNER_BLOB,
    E37A: E37A_BLOB,
    R2SRC: R2SRC_BLOB,
    A2E: A2E_BLOB,
    SG7D: SG7D_BLOB,
    SG7A: SG7A_BLOB,
    E36: E36_BLOB,
}

OUT_TOKEN = "POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_R1_R1_R1_R2_R1_R1_R1_R1_R1"
OUT_REL = BASE / (OUT_TOKEN + "_ZeroTarget_CV_EqualityDomain_Repair_Feasibility_and_FullPropagation_Audit")
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


def build_xy1_support(exact_cv: np.ndarray, exact_cell: np.ndarray):
    """Exact CV-cell support plus one same-layer X/Y face-neighbor terminal shell."""
    exact_cv = np.asarray(exact_cv, dtype=np.int64)
    exact_cell = np.asarray(exact_cell, dtype=np.int64)
    k = exact_cell // (NY * NX)
    rem = exact_cell % (NY * NX)
    j = rem // NX
    i = rem % NX

    keys = [exact_cv * NCELL + exact_cell]
    shells = [np.zeros(len(exact_cv), dtype=np.int8)]

    for dj, di in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        jj = j + dj
        ii = i + di
        valid = (jj >= 0) & (jj < NY) & (ii >= 0) & (ii < NX)
        cell2 = (k[valid] * NY + jj[valid]) * NX + ii[valid]
        keys.append(exact_cv[valid] * NCELL + cell2)
        shells.append(np.ones(int(np.count_nonzero(valid)), dtype=np.int8))

    key = np.concatenate(keys)
    shell = np.concatenate(shells)

    # Sort by key, then shell so exact support (shell 0) wins duplicate pairs.
    order = np.lexsort((shell, key))
    key = key[order]
    shell = shell[order]
    first = np.empty(len(key), dtype=bool)
    first[0] = True
    first[1:] = key[1:] != key[:-1]
    key = key[first]
    shell = shell[first]

    return (key // NCELL).astype(np.int64), (key % NCELL).astype(np.int64), shell


def selftest():
    cv = np.asarray([0], dtype=np.int64)
    cell = np.asarray([(2 * NY + 10) * NX + 10], dtype=np.int64)
    ecv, ecell, shell = build_xy1_support(cv, cell)
    assert len(ecv) == 5
    assert int(np.count_nonzero(shell == 0)) == 1
    assert int(np.count_nonzero(shell == 1)) == 4
    print("POSTV16 AV4 PIVOT P2-R6-R29-R3-R2-R1-R1-R1-R2-R1-R1-R1-R1-R1 structural self-test: PASS")


def main(project_root: Path, drive_root: Path) -> int:
    from scipy.optimize import linprog
    from scipy.sparse import coo_matrix, vstack, hstack, csr_matrix, eye

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

        stage = "parent_diagnostic_Git_authority"
        gate("current_parent_runner_blob_bound", gt(root, "hash-object", str(root / CURRENT_PARENT_RUNNER)) == CURRENT_PARENT_RUNNER_BLOB)

        stage = "foundational_R25_authority"
        r25 = drive / R25_REL
        m25 = manifest(r25, R25_MANIFEST)
        state_path = r25 / R25_STATE
        gate("R25_state_manifest_SHA_exact", m25.get(R25_STATE) == R25_SHA)
        gate("R25_state_file_SHA_exact", state_path.is_file() and sha(state_path) == R25_SHA)

        with np.load(state_path, allow_pickle=False) as z:
            grid_parent = np.asarray(z["cartesian_component_mass_kg"], dtype=np.float64)
            represented_parent = np.asarray(z["represented_cartesian_cell_mass_kg"], dtype=np.float64)
            residual_parent = np.asarray(z["grid_residual_component_mass_kg"], dtype=np.float64)
            old_cv_mass = np.asarray(z["transport_CV_component_mass_kg"], dtype=np.float64)
            old_cv_sat = np.asarray(z["transport_CV_saturation"], dtype=np.float64)
            xyz = np.asarray(z["streamline_xyz_m"], dtype=np.float64)
            tof_s = np.asarray(z["streamline_tof_s"], dtype=np.float64)
            weights_m3_s = np.asarray(z["streamline_weight_m3_s"], dtype=np.float64)
            pressure = np.asarray(z["refreshed_pressure_psi"], dtype=np.float64)
            p_ref = float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))
            exact_cv = np.asarray(z["exact_support_edge_cv"], dtype=np.int64)
            exact_cell = np.asarray(z["exact_support_edge_cell"], dtype=np.int64)
            exact_x = np.asarray(z["exact_support_edge_assigned_mass_kg"], dtype=np.float64)
            exact_frontier = float(np.asarray(z["stage1_maximum_representable_mass_kg"]).reshape(()))

        gate(
            "parent_shapes_exact",
            grid_parent.shape == GRID
            and represented_parent.shape == GRID
            and residual_parent.shape == GRID
            and old_cv_mass.shape == (NSL, NCV)
            and old_cv_sat.shape == (NSL, NCV)
            and xyz.shape == (NSL, NN, 3)
            and tof_s.shape == (NSL, NN)
            and weights_m3_s.shape == (NSL,),
        )
        gate("parent_split_identity", float(np.max(np.abs(grid_parent - represented_parent - residual_parent))) <= MASS_TOL)
        parent_rep_total = float(np.sum(represented_parent))
        gate("parent_at_exact_support_frontier", abs(exact_frontier - parent_rep_total) <= MASS_TOL,
             exact_frontier - parent_rep_total)
        gate("exact_edge_assignment_total", abs(float(np.sum(exact_x)) - parent_rep_total) <= MASS_TOL,
             float(np.sum(exact_x)) - parent_rep_total)

        stage = "foundational_A6E_authority"
        a6e = drive / A6E_REL / A6E_STATE
        gate("A6E_state_SHA_exact", a6e.is_file() and sha(a6e) == A6E_SHA)
        with np.load(a6e, allow_pickle=False) as z:
            phi = np.asarray(z["paired_porosity"], dtype=np.float64)
        gate("paired_porosity_valid", phi.shape == GRID and np.all(phi > 0.0) and np.isfinite(phi).all())

        stage = "theory_transport_reconstruction"
        e37a = load_module(root / E37A, "recon_e37a")
        r2 = load_module(root / R2SRC, "recon_r2")
        a2e = load_module(root / A2E, "recon_a2e")
        sg7d = load_module(root / SG7D, "recon_sg7d")
        sg7a = load_module(root / SG7A, "recon_sg7a")
        e36 = load_module(root / E36, "recon_e36")

        op = sg7d.build_subsegment_operator(
            xyz,
            tof_s / DAY_TO_S,
            weights_m3_s * DAY_TO_S,
        )
        geometry = e37a.build_control_volume_geometry(r2, op, pressure, p_ref, NSL, NCV)
        face_pressure = e37a.build_face_pressure(e36, sg7d, xyz, pressure)

        xi = np.linspace(0.0, 1.0, NCV + 1, dtype=np.float64)
        u_face = np.asarray(sg7a.u_dimensionless(xi), dtype=np.float64)
        q = weights_m3_s * DAY_TO_S
        rho_ref = float(e37a.CO2_RHO_REF_KG_M3)

        theory_flux = np.zeros((NSL, NCV + 1), dtype=np.float64)
        theory_flux[:, 0] = q * rho_ref

        donor = old_cv_sat[:, :-1]
        donor_ff = np.asarray(sg7a.fractional_flow(donor), dtype=np.float64)
        theory_flux[:, 1:-1] = (
            q[:, None] * u_face[None, 1:-1] * donor_ff * rho_ref
        )
        outlet_sat = old_cv_sat[:, -1]
        outlet_ff = np.asarray(sg7a.fractional_flow(outlet_sat), dtype=np.float64)
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
        cv_cap_tol = max(1e-9, 1e-12 * max(float(np.max(np.abs(new_cv_mass))), 1.0))
        gate("theory_CV_capacity_pass", float(np.max(new_cv_mass - cv_capacity)) <= cv_cap_tol,
             float(np.max(new_cv_mass - cv_capacity)))
        gate("theory_CV_nonnegative", float(np.min(new_cv_mass)) >= -MASS_TOL, float(np.min(new_cv_mass)))

        injected = float(np.sum(theory_flux[:, 0]) * DT)
        produced = float(np.sum(theory_flux[:, -1]) * DT)
        cv_delta = float(np.sum(new_cv_mass) - np.sum(old_cv_mass))
        cv_source_sink = cv_delta - injected + produced
        gate("theory_CV_source_sink_closure", abs(cv_source_sink) <= MASS_TOL, cv_source_sink)

        new_total = float(np.sum(new_cv_mass))
        frontier_shortfall = new_total - exact_frontier
        gate("exact_support_deadlock_reconstructed", frontier_shortfall > MASS_TOL, frontier_shortfall)

        stage = "direct_delta_target_reconstruction"
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
        gate("CV_to_subsegment_delta_closure", abs(sub_delta_total - cv_delta) <= MASS_TOL,
             sub_delta_total - cv_delta)

        delta_grid = np.bincount(flat, weights=sub_delta, minlength=NCELL).reshape(GRID)
        gate("subsegment_to_grid_delta_closure", abs(float(np.sum(delta_grid)) - sub_delta_total) <= MASS_TOL,
             float(np.sum(delta_grid)) - sub_delta_total)

        direct_target_rep = represented_parent + delta_grid
        gate("direct_target_total_matches_new_CV_total",
             abs(float(np.sum(direct_target_rep)) - new_total) <= 1e-5,
             float(np.sum(direct_target_rep)) - new_total)

        stage = "XY1_support_reconstruction"
        edge_cv, edge_cell, shell = build_xy1_support(exact_cv, exact_cell)
        nedge = len(edge_cv)
        gate("XY1_edge_count_expanded", nedge > len(exact_cv), [len(exact_cv), nedge])

        hetero_pv = phi * float(a2e.BULK_VOLUME_M3)
        full_sat = np.full(GRID, float(a2e.INJECTED), dtype=np.float64)
        cart_capacity = np.asarray(
            a2e.local_mass(r2, full_sat, pressure, p_ref, hetero_pv),
            dtype=np.float64,
        )
        rep_capacity = cart_capacity - residual_parent
        cart_cap_tol = max(1e-8, 1e-12 * max(float(np.max(cart_capacity)), 1.0))
        gate("represented_capacity_nonnegative", float(np.min(rep_capacity)) >= -cart_cap_tol,
             float(np.min(rep_capacity)))
        rep_capacity = np.maximum(rep_capacity, 0.0).reshape(-1)

        stage = "equality_domain_root_cause_reconstruction"
        target_cv_flat = new_cv_mass.reshape(-1)
        positive_cv = np.where(target_cv_flat > MASS_TOL)[0]
        zero_target_cv = np.where(target_cv_flat <= MASS_TOL)[0]
        gate("zero_target_CVs_present", len(zero_target_cv) > 0, len(zero_target_cv))

        # Historical flawed equality domain: only strictly positive-target CVs.
        cvmap = np.full(NCVT, -1, dtype=np.int64)
        cvmap[positive_cv] = np.arange(len(positive_cv), dtype=np.int64)
        rr = cvmap[edge_cv]
        mask = rr >= 0
        cols = np.nonzero(mask)[0]
        Aeq_positive = coo_matrix(
            (np.ones(len(cols), dtype=np.float64), (rr[mask], cols)),
            shape=(len(positive_cv), nedge),
        ).tocsr()
        beq_positive = target_cv_flat[positive_cv]

        # Correct intended equality domain: EVERY CV in the transport state.
        Aeq_all = coo_matrix(
            (
                np.ones(nedge, dtype=np.float64),
                (edge_cv, np.arange(nedge, dtype=np.int64)),
            ),
            shape=(NCVT, nedge),
        ).tocsr()
        beq_all = target_cv_flat.copy()
        all_row_degree = np.diff(Aeq_all.indptr)
        gate("every_CV_has_XY1_support", int(np.min(all_row_degree)) > 0,
             [int(np.min(all_row_degree)), int(np.max(all_row_degree))])
        gate("all_CV_equality_row_count_exact", Aeq_all.shape[0] == NCVT, Aeq_all.shape)

        Acell = coo_matrix(
            (
                np.ones(nedge, dtype=np.float64),
                (edge_cell, np.arange(nedge, dtype=np.int64)),
            ),
            shape=(NCELL, nedge),
        ).tocsr()
        c1 = (shell > 0).astype(np.float64)

        def solve_stage1(Aeq_base, beq_base, label):
            lp = linprog(
                c1,
                A_ub=Acell,
                b_ub=rep_capacity,
                A_eq=Aeq_base,
                b_eq=beq_base,
                bounds=(0.0, None),
                method="highs-ds",
                options={
                    "presolve": True,
                    "primal_feasibility_tolerance": HIGHS_PRIMAL_FEASIBILITY_TOL,
                    "dual_feasibility_tolerance": HIGHS_DUAL_FEASIBILITY_TOL,
                },
            )
            gate(f"{label}_stage1_feasible", lp.success, [lp.status, lp.message])
            return float(lp.fun)

        stage = "stage1_domain_comparison"
        flawed_halo_opt = solve_stage1(Aeq_positive, beq_positive, "positive_only")
        corrected_halo_opt = solve_stage1(Aeq_all, beq_all, "all_CV")
        gate("corrected_stage1_terminal_mass_positive", corrected_halo_opt > 0.0, corrected_halo_opt)

        stage = "lexicographic_stage2_construction"
        nd = NCELL
        zero_d = csr_matrix((NCELL, nd), dtype=np.float64)
        A_cap = hstack([Acell, zero_d], format="csr")
        I = eye(nd, format="csr", dtype=np.float64)
        A_abs_pos = hstack([Acell, -I], format="csr")
        A_abs_neg = hstack([-Acell, -I], format="csr")
        target = direct_target_rep.reshape(-1)
        c2 = np.concatenate([np.zeros(nedge, dtype=np.float64), np.ones(nd, dtype=np.float64)])
        bounds = [(0.0, None)] * (nedge + nd)

        def solve_stage2(label, Aeq_base, beq_base, halo_opt, *, scaled=False):
            halo_row = csr_matrix(c1.reshape(1, -1))
            zero1 = csr_matrix((1, nd), dtype=np.float64)
            A_halo_pos = hstack([halo_row, zero1], format="csr")
            A_halo_neg = hstack([-halo_row, zero1], format="csr")
            b_halo = np.asarray([halo_opt + HALO_OPT_TOL, -halo_opt + HALO_OPT_TOL], dtype=np.float64)
            A_ub = vstack([A_cap, A_abs_pos, A_abs_neg, A_halo_pos, A_halo_neg], format="csr")
            b_ub = np.concatenate([rep_capacity, target, -target, b_halo])
            Aeq2 = hstack([Aeq_base, csr_matrix((Aeq_base.shape[0], nd), dtype=np.float64)], format="csr")

            if scaled:
                eq_floor = 1.0e-3
                scale = 1.0 / np.maximum(np.abs(beq_base), eq_floor)
                Aeq_use = Aeq2.multiply(scale[:, None]).tocsr()
                beq_use = beq_base * scale
            else:
                Aeq_use = Aeq2
                beq_use = beq_base

            lp = linprog(
                c2,
                A_ub=A_ub,
                b_ub=b_ub,
                A_eq=Aeq_use,
                b_eq=beq_use,
                bounds=bounds,
                method="highs-ds",
                options={
                    "presolve": True,
                    "primal_feasibility_tolerance": HIGHS_PRIMAL_FEASIBILITY_TOL,
                    "dual_feasibility_tolerance": HIGHS_DUAL_FEASIBILITY_TOL,
                },
            )
            result = {
                "method": label,
                "scaled_equalities": bool(scaled),
                "solver_success": bool(lp.success),
                "solver_status": int(lp.status),
                "solver_message": str(lp.message),
                "equality_row_count": int(Aeq_base.shape[0]),
                "halo_optimum_kg": float(halo_opt),
            }
            arrays = {}
            if not lp.success:
                result["full_propagation_pass"] = False
                return result, arrays

            z = np.asarray(lp.x, dtype=np.float64)
            x = z[:nedge]
            d = z[nedge:]
            cv_check = np.bincount(edge_cv, weights=x, minlength=NCVT).reshape(NSL, NCV)
            resid = cv_check - new_cv_mass
            absres = np.abs(resid)
            max_flat = int(np.argmax(absres))
            max_sl, max_cv = divmod(max_flat, NCV)
            zero_cv_assigned = cv_check.reshape(-1)[zero_target_cv]

            halo = float(np.sum(x[shell > 0]))
            cell_rep = np.bincount(edge_cell, weights=x, minlength=NCELL).reshape(GRID)
            candidate = cell_rep + residual_parent
            L1_exact = float(np.sum(np.abs(cell_rep - direct_target_rep)))
            d_err = float(np.max(np.abs(d - np.abs(cell_rep.reshape(-1) - target))))
            min_rep = float(np.min(cell_rep))
            cap_excess = float(np.max(candidate - cart_capacity))
            split_err = float(np.max(np.abs(candidate - cell_rep - residual_parent)))
            expected_total = float(np.sum(grid_parent)) + injected - produced
            source_sink_residual = float(np.sum(candidate)) - expected_total
            global_tol = max(MASS_TOL, REL_TOL * max(abs(expected_total), 1.0))

            inversion_pass = False
            recon_err = None
            sat_min = None
            sat_max = None
            if min_rep >= -MASS_TOL and cap_excess <= cart_cap_tol:
                csg = np.asarray(a2e.invert_local_mass(r2, candidate, pressure, p_ref, hetero_pv), dtype=np.float64)
                csat = float(a2e.BACKGROUND) + csg
                recon = np.asarray(a2e.local_mass(r2, csat, pressure, p_ref, hetero_pv), dtype=np.float64)
                recon_err = float(np.max(np.abs(recon - candidate)))
                sat_min = float(np.min(csat)); sat_max = float(np.max(csat))
                inversion_pass = recon_err <= 1e-8 and sat_min >= BACKGROUND - SAT_TOL and sat_max <= MAX_SAT + SAT_TOL

            cv_pass = float(np.max(absres)) <= MASS_TOL
            halo_pass = abs(halo - halo_opt) <= 2 * HALO_OPT_TOL
            l1_pass = abs(float(lp.fun) - L1_exact) <= max(1e-5, 1e-10 * max(L1_exact, 1.0))
            d_pass = d_err <= 1e-5
            downstream = (
                cv_pass and halo_pass and l1_pass and d_pass
                and min_rep >= -MASS_TOL and cap_excess <= cart_cap_tol
                and split_err <= MASS_TOL and abs(source_sink_residual) <= global_tol
                and inversion_pass
            )
            result.update({
                "CV_equality_max_abs_error_kg": float(np.max(absres)),
                "CV_equality_violation_count": int(np.count_nonzero(absres > MASS_TOL)),
                "CV_equality_L1_error_kg": float(np.sum(absres)),
                "max_error_streamline_index": int(max_sl),
                "max_error_CV_index": int(max_cv),
                "max_error_signed_kg": float(resid[max_sl, max_cv]),
                "max_error_target_CV_mass_kg": float(new_cv_mass[max_sl, max_cv]),
                "zero_target_CV_count": int(len(zero_target_cv)),
                "zero_target_CV_total_assigned_mass_kg": float(np.sum(zero_cv_assigned)),
                "zero_target_CV_max_assigned_mass_kg": float(np.max(zero_cv_assigned)) if len(zero_cv_assigned) else 0.0,
                "stage2_terminal_mass_kg": halo,
                "stage2_cell_L1_deviation_kg": L1_exact,
                "stage2_abs_auxiliary_max_error_kg": d_err,
                "minimum_represented_mass_kg": min_rep,
                "cartesian_max_capacity_excess_kg": cap_excess,
                "split_identity_max_abs_error_kg": split_err,
                "cartesian_source_sink_residual_kg": source_sink_residual,
                "cartesian_mass_reconstruction_max_abs_error_kg": recon_err,
                "candidate_saturation_min": sat_min,
                "candidate_saturation_max": sat_max,
                "CV_equality_pass": cv_pass,
                "halo_optimum_pass": halo_pass,
                "L1_exact_pass": l1_pass,
                "abs_auxiliary_pass": d_pass,
                "cartesian_inversion_pass": inversion_pass,
                "full_propagation_pass": bool(downstream),
            })
            arrays = {
                "edge_allocation_kg": x,
                "represented_candidate_kg": cell_rep,
                "CV_equality_residual_kg": resid,
            }
            return result, arrays

        stage = "historical_omission_reproduction"
        flawed_result, flawed_arrays = solve_stage2(
            "positive_target_only_historical",
            Aeq_positive,
            beq_positive,
            flawed_halo_opt,
            scaled=False,
        )
        gate("historical_zero_target_ghost_mass_reproduced",
             flawed_result.get("zero_target_CV_total_assigned_mass_kg", 0.0) > MASS_TOL,
             flawed_result.get("zero_target_CV_total_assigned_mass_kg"))
        gate("historical_worst_error_targets_zero_mass_CV",
             abs(float(flawed_result.get("max_error_target_CV_mass_kg", 1.0))) <= MASS_TOL,
             flawed_result.get("max_error_target_CV_mass_kg"))
        ghost_total = float(flawed_result["zero_target_CV_total_assigned_mass_kg"])
        ghost_source = float(flawed_result["cartesian_source_sink_residual_kg"])
        gate("ghost_mass_explains_global_source_sink_error",
             abs(ghost_total - ghost_source) <= 2.0e-5,
             [ghost_total, ghost_source])

        stage = "all_CV_equality_domain_repair_audit"
        all_unscaled, arr_unscaled = solve_stage2(
            "all_CV_unscaled",
            Aeq_all,
            beq_all,
            corrected_halo_opt,
            scaled=False,
        )
        all_scaled, arr_scaled = solve_stage2(
            "all_CV_row_scaled",
            Aeq_all,
            beq_all,
            corrected_halo_opt,
            scaled=True,
        )
        results = {
            "historical_positive_target_only": flawed_result,
            "all_CV_unscaled": all_unscaled,
            "all_CV_row_scaled": all_scaled,
        }
        method_arrays = {
            "historical_positive_target_only": flawed_arrays,
            "all_CV_unscaled": arr_unscaled,
            "all_CV_row_scaled": arr_scaled,
        }
        passing = [name for name in ("all_CV_unscaled", "all_CV_row_scaled") if results[name].get("full_propagation_pass") is True]
        preferred = "all_CV_unscaled" if "all_CV_unscaled" in passing else ("all_CV_row_scaled" if "all_CV_row_scaled" in passing else None)

        if preferred is not None:
            classification = "ZERO_TARGET_CV_EQUALITY_DOMAIN_OMISSION_CONFIRMED_ALL_CV_EQUALITY_REPAIR_PASSES_FULL_PROPAGATION"
        else:
            classification = "ZERO_TARGET_CV_EQUALITY_DOMAIN_OMISSION_CONFIRMED_BUT_ALL_CV_EQUALITY_REPAIR_HAS_ADDITIONAL_DOWNSTREAM_OR_NUMERICAL_FAILURE"

        stage = "diagnostic_publication"
        out.mkdir(parents=True, exist_ok=False)
        arrays = {
            "XY1_edge_cv": edge_cv,
            "XY1_edge_cell": edge_cell,
            "XY1_edge_shell_cost": shell,
            "theory_transport_new_CV_mass_kg": new_cv_mass,
            "direct_delta_represented_target_kg": direct_target_rep,
            "zero_target_CV_indices": zero_target_cv,
        }
        for method_name, arrs in method_arrays.items():
            for key, value in arrs.items():
                arrays[f"{method_name}_{key}"] = value
        arrays_name = f"{OUT_TOKEN}_ZeroTarget_CV_EqualityDomain_Audit_Arrays.npz"
        (out / arrays_name).write_bytes(deterministic_npz_bytes(arrays))
        arrays_sha = sha(out / arrays_name)

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": classification,
            "root_cause": "historical Stage1/Stage2 equality matrices constrained only CVs with target mass > MASS_TOL; zero-target CV support edges remained unconstrained and Stage2 L1 optimization populated them with ghost represented mass",
            "positive_target_CV_count": int(len(positive_cv)),
            "zero_target_CV_count": int(len(zero_target_cv)),
            "all_CV_count": int(NCVT),
            "historical_equality_row_count": int(Aeq_positive.shape[0]),
            "corrected_equality_row_count": int(Aeq_all.shape[0]),
            "historical_stage1_minimum_terminal_mass_kg": flawed_halo_opt,
            "corrected_stage1_minimum_terminal_mass_kg": corrected_halo_opt,
            "solver_results": results,
            "full_propagation_passing_corrected_methods": passing,
            "preferred_corrected_equality_method": preferred,
            "diagnostic_arrays_sha256": arrays_sha,
            "state_mutation_executed": False,
            "support_growth_executed": False,
            "physical_time_advance_executed": False,
            "R30_authorized": False,
            "P3_authorized": False,
        }
        decision = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "P2_R6_R29_R3_R2_R1_R1_R1_R2_R1_R1_R1_R1_R1_R2_authorized": preferred is not None,
            "P2_R6_R29_R3_R2_R1_R1_R1_R2_R1_R1_R1_R1_R1_R2_name": "All-CV Equality-Domain Theory-Flux + XY1 Repair Design Freeze",
            "P2_R6_R29_R3_R2_R1_R1_R1_R2_R1_R1_R1_R1_R1_R2_design_only": True,
            "P2_R6_R29_R3_R2_R1_R1_R1_R2_R1_R1_R1_R1_R1_R2_execution_authorized": False,
            "preferred_corrected_equality_method": preferred,
            "all_CV_equality_domain_required": preferred is not None,
            "zero_target_CV_edges_must_be_constrained_to_zero_total_mass": preferred is not None,
            "science_CV_equality_gate_kg": MASS_TOL,
            "science_gate_enlargement_authorized": False,
            "flux_law_change_authorized": False,
            "support_topology_change_authorized": False,
            "support_beyond_XY1_authorized": False,
            "residual_sidecar_mutation_authorized": False,
            "nominal_dt_change_authorized": False,
            "physical_time_advance_authorized": False,
            "R30_authorized": False,
            "P3_authorized": False,
        }
        (out / f"PAD_Stream_{OUT_TOKEN}_Summary.json").write_bytes(jb(summary))
        (out / f"{OUT_TOKEN}_Decision_Contract.json").write_bytes(jb(decision))
        (out / f"{OUT_TOKEN}_Final_Gate_Matrix.csv").write_bytes(csvb(gates))
        rows=[]
        for p in sorted(out.iterdir()):
            if p.is_file(): rows.append({"file":p.name,"sha256":sha(p),"bytes":p.stat().st_size})
        (out / f"{OUT_TOKEN}_Artifact_Manifest.csv").write_bytes(csvb(rows))

        print("=" * 200)
        print(M, "PASS")
        print("Classification                         :", classification)
        print("Positive-target / zero-target CVs      :", len(positive_cv), "/", len(zero_target_cv))
        print("Historical equality rows               :", Aeq_positive.shape[0])
        print("Corrected equality rows                :", Aeq_all.shape[0])
        print("Historical ghost CV mass kg            :", ghost_total)
        print("Historical source/sink residual kg     :", ghost_source)
        print("Historical / corrected halo opt kg     :", flawed_halo_opt, "/", corrected_halo_opt)
        for name, r in results.items():
            print(name, "CV max err=", r.get("CV_equality_max_abs_error_kg"), "zero-CV mass=", r.get("zero_target_CV_total_assigned_mass_kg"), "full=", r.get("full_propagation_pass"))
        print("Passing corrected methods              :", passing)
        print("Preferred corrected equality method    :", preferred)
        print("Next design freeze authorized          :", preferred is not None)
        print("State / time / R30                     : False / False / False")
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
                "missing_intermediate_artifacts_not_fabricated": True,
                "prior_scientific_results_preserved": True,
                "state_mutation_executed": False,
                "support_growth_executed": False,
                "physical_time_advance_executed": False,
                "R30_authorized": False,
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
