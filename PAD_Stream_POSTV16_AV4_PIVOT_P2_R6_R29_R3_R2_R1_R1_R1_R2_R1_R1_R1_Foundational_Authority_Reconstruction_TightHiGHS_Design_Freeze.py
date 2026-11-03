#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, hashlib, importlib.util, io, json, subprocess, sys, zipfile
from pathlib import Path
from typing import Any
import numpy as np

M = "POSTV16-AV4-PIVOT-P2-R6-R29-R3-R2-R1-R1-R1-R2-R1-R1-R1"
NAME = "Foundational-Authority Reconstruction + Tight-HiGHS Comprehensive Repair Design Freeze"

PASS = (
    "AV4PIVOTP2R6R29R3R2R1R1R1R2R1R1R1_FOUNDATIONAL_AUTHORITY_RECONSTRUCTION_"
    "TIGHT_HIGHS_COMPREHENSIVE_REPAIR_DESIGN_FREEZE_PASS_NO_STATE_MUTATION"
)
BLOCK = "AV4PIVOTP2R6R29R3R2R1R1R1R2R1R1R1_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "80adcafe02757a9f8fdf0f1a40a0b9705d7b6e09"

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

SOURCE_BLOBS = {
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

OUT_TOKEN = "POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_R1_R1_R1_R2_R1_R1_R1"
OUT_REL = BASE / (
    OUT_TOKEN + "_Foundational_Authority_Reconstruction_TightHiGHS_Design_Freeze"
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
    print("POSTV16 AV4 PIVOT P2-R6-R29-R3-R2-R1-R1-R1-R2-R1-R1-R1 structural self-test: PASS")


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

        active = np.where(new_cv_mass.reshape(-1) > MASS_TOL)[0]
        cvmap = np.full(NCVT, -1, dtype=np.int64)
        cvmap[active] = np.arange(len(active), dtype=np.int64)

        rr = cvmap[edge_cv]
        mask = rr >= 0
        cols = np.nonzero(mask)[0]
        Aeq = coo_matrix(
            (np.ones(len(cols), dtype=np.float64), (rr[mask], cols)),
            shape=(len(active), nedge),
        ).tocsr()
        beq = new_cv_mass.reshape(-1)[active]

        Acell = coo_matrix(
            (
                np.ones(nedge, dtype=np.float64),
                (edge_cell, np.arange(nedge, dtype=np.int64)),
            ),
            shape=(NCELL, nedge),
        ).tocsr()

        stage = "XY1_stage1_minimum_terminal_mass"
        c1 = (shell > 0).astype(np.float64)
        lp1 = linprog(
            c1,
            A_ub=Acell,
            b_ub=rep_capacity,
            A_eq=Aeq,
            b_eq=beq,
            bounds=(0.0, None),
            method="highs",
            options={"presolve": True},
        )
        gate("XY1_stage1_feasible", lp1.success, [lp1.status, lp1.message])
        halo_opt = float(lp1.fun)
        gate("XY1_stage1_positive_terminal_mass", halo_opt > 0.0, halo_opt)

        stage = "lexicographic_stage2_construction"
        nd = NCELL
        zero_d = csr_matrix((NCELL, nd), dtype=np.float64)
        A_cap = hstack([Acell, zero_d], format="csr")
        b_cap = rep_capacity

        # IMPORTANT: genuinely sparse identity; never allocate np.eye(37500).
        I = eye(nd, format="csr", dtype=np.float64)
        A_abs_pos = hstack([Acell, -I], format="csr")
        A_abs_neg = hstack([-Acell, -I], format="csr")
        target = direct_target_rep.reshape(-1)
        b_abs_pos = target
        b_abs_neg = -target

        halo_row = csr_matrix(c1.reshape(1, -1))
        zero1 = csr_matrix((1, nd), dtype=np.float64)
        A_halo_pos = hstack([halo_row, zero1], format="csr")
        A_halo_neg = hstack([-halo_row, zero1], format="csr")
        b_halo = np.asarray(
            [halo_opt + HALO_OPT_TOL, -halo_opt + HALO_OPT_TOL],
            dtype=np.float64,
        )

        A_ub = vstack(
            [A_cap, A_abs_pos, A_abs_neg, A_halo_pos, A_halo_neg],
            format="csr",
        )
        b_ub = np.concatenate([b_cap, b_abs_pos, b_abs_neg, b_halo])
        Aeq2 = hstack([Aeq, csr_matrix((Aeq.shape[0], nd), dtype=np.float64)], format="csr")
        c2 = np.concatenate([np.zeros(nedge, dtype=np.float64), np.ones(nd, dtype=np.float64)])
        bounds = [(0.0, None)] * (nedge + nd)

        stage = "default_HiGHS_parent_failure_reproduction"
        lp_default = linprog(
            c2,
            A_ub=A_ub,
            b_ub=b_ub,
            A_eq=Aeq2,
            b_eq=beq,
            bounds=bounds,
            method="highs",
            options={"presolve": True},
        )
        gate("default_stage2_feasible", lp_default.success, [lp_default.status, lp_default.message])
        xd = np.asarray(lp_default.x[:nedge], dtype=np.float64)
        cv_default = np.bincount(edge_cv, weights=xd, minlength=NCVT).reshape(NSL, NCV)
        default_cv_err = float(np.max(np.abs(cv_default - new_cv_mass)))
        gate("default_CV_equality_failure_reproduced", default_cv_err > MASS_TOL,
             [default_cv_err, MASS_TOL])

        stage = "tight_HiGHS_technical_repair"
        lp_tight = linprog(
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
        gate("tight_stage2_feasible", lp_tight.success, [lp_tight.status, lp_tight.message])

        z = np.asarray(lp_tight.x, dtype=np.float64)
        x = z[:nedge]
        d = z[nedge:]

        halo2 = float(np.sum(x[shell > 0]))
        cell_rep = np.bincount(edge_cell, weights=x, minlength=NCELL).reshape(GRID)
        candidate = cell_rep + residual_parent
        cv_check = np.bincount(edge_cv, weights=x, minlength=NCVT).reshape(NSL, NCV)
        cv_err = float(np.max(np.abs(cv_check - new_cv_mass)))

        L1_exact = float(np.sum(np.abs(cell_rep - direct_target_rep)))
        d_err = float(np.max(np.abs(d - np.abs(cell_rep.reshape(-1) - target))))
        min_rep = float(np.min(cell_rep))
        cap_excess = float(np.max(candidate - cart_capacity))
        split_err = float(np.max(np.abs(candidate - cell_rep - residual_parent)))

        expected_total = float(np.sum(grid_parent)) + injected - produced
        source_sink_residual = float(np.sum(candidate)) - expected_total
        global_tol = max(MASS_TOL, REL_TOL * max(abs(expected_total), 1.0))

        candidate_sg = np.asarray(
            a2e.invert_local_mass(r2, candidate, pressure, p_ref, hetero_pv),
            dtype=np.float64,
        )
        candidate_sat = float(a2e.BACKGROUND) + candidate_sg
        reconstructed = np.asarray(
            a2e.local_mass(r2, candidate_sat, pressure, p_ref, hetero_pv),
            dtype=np.float64,
        )
        recon_err = float(np.max(np.abs(reconstructed - candidate)))

        stage = "comprehensive_design_gates"
        gate("tight_CV_mass_equalities", cv_err <= MASS_TOL, cv_err)
        gate("stage2_halo_optimum_preserved", abs(halo2 - halo_opt) <= 2 * HALO_OPT_TOL,
             [halo2, halo_opt])
        gate("stage2_reported_L1_exact",
             abs(float(lp_tight.fun) - L1_exact) <= max(1e-5, 1e-10 * max(L1_exact, 1.0)),
             [lp_tight.fun, L1_exact])
        gate("stage2_abs_auxiliary_exact", d_err <= 1e-5, d_err)
        gate("represented_nonnegative", min_rep >= -MASS_TOL, min_rep)
        gate("heterogeneous_cartesian_capacity", cap_excess <= cart_cap_tol,
             [cap_excess, cart_cap_tol])
        gate("split_identity", split_err <= MASS_TOL, split_err)
        gate("source_sink_closure", abs(source_sink_residual) <= global_tol,
             [source_sink_residual, global_tol])
        gate("cartesian_EOS_reconstruction", recon_err <= 1e-8, recon_err)
        gate(
            "candidate_saturation_bounds",
            float(np.min(candidate_sat)) >= BACKGROUND - SAT_TOL
            and float(np.max(candidate_sat)) <= MAX_SAT + SAT_TOL,
            [float(np.min(candidate_sat)), float(np.max(candidate_sat))],
        )

        stage = "design_publication"
        out.mkdir(parents=True, exist_ok=False)

        arrays = {
            "XY1_edge_cv": edge_cv,
            "XY1_edge_cell": edge_cell,
            "XY1_edge_shell_cost": shell,
            "stage1_minimum_terminal_mass_kg": np.asarray(halo_opt),
            "tight_stage2_edge_allocation_kg": x,
            "tight_stage2_represented_candidate_kg": cell_rep,
            "tight_stage2_candidate_grid_mass_kg": candidate,
            "tight_stage2_candidate_saturation": candidate_sat,
            "theory_transport_new_CV_mass_kg": new_cv_mass,
            "theory_transport_new_CV_saturation": new_cv_sat,
            "theory_face_mass_flux_kg_day": theory_flux,
            "direct_delta_represented_target_kg": direct_target_rep,
            "residual_parent_frozen_kg": residual_parent,
        }
        frozen_name = f"{OUT_TOKEN}_Frozen_Prospective_TheoryFlux_XY1_Candidate.npz"
        (out / frozen_name).write_bytes(deterministic_npz_bytes(arrays))
        frozen_sha = sha(out / frozen_name)

        classification = (
            "FOUNDATIONAL_RECONSTRUCTION_REPRODUCED_DEFAULT_HIGHS_CV_EQUALITY_BLOCK_"
            "AND_TIGHT_HIGHS_CLOSED_THEORY_FLUX_XY1_REPAIR_DESIGN"
        )

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": classification,
            "intermediate_support_audit_artifacts_required": False,
            "intermediate_flux_audit_artifacts_required": False,
            "intermediate_remap_audit_artifacts_required": False,
            "authority_reconstructed_from": [
                "R25-R3 accepted split state",
                "A6E heterogeneous porosity state",
                "frozen repository transport/mapback/EOS source code",
            ],
            "R25_exact_support_frontier_kg": exact_frontier,
            "R25_parent_represented_total_kg": parent_rep_total,
            "theory_candidate_CV_total_kg": new_total,
            "theory_candidate_exact_support_frontier_shortfall_kg": frontier_shortfall,
            "XY1_edge_count": int(nedge),
            "stage1_minimum_terminal_mass_kg": halo_opt,
            "default_HiGHS_CV_equality_max_abs_error_kg": default_cv_err,
            "tight_HiGHS_CV_equality_max_abs_error_kg": cv_err,
            "HiGHS_primal_feasibility_tolerance": HIGHS_PRIMAL_FEASIBILITY_TOL,
            "HiGHS_dual_feasibility_tolerance": HIGHS_DUAL_FEASIBILITY_TOL,
            "stage2_terminal_mass_kg": halo2,
            "stage2_cell_L1_deviation_from_direct_delta_target_kg": L1_exact,
            "stage2_used_terminal_edge_count": int(np.count_nonzero((shell > 0) & (x > MASS_TOL))),
            "minimum_represented_mass_kg": min_rep,
            "cartesian_max_capacity_excess_kg": cap_excess,
            "cartesian_source_sink_residual_kg": source_sink_residual,
            "cartesian_mass_reconstruction_max_abs_error_kg": recon_err,
            "candidate_saturation_min": float(np.min(candidate_sat)),
            "candidate_saturation_max": float(np.max(candidate_sat)),
            "frozen_prospective_candidate_sha256": frozen_sha,
            "dense_identity_allocated": False,
            "state_mutation_executed": False,
            "support_growth_executed": False,
            "physical_time_advance_executed": False,
            "R30_authorized": False,
            "P3_authorized": False,
        }

        protocol = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "repair_scope": {
                "transport_flux_law": "q * u_D(xi) * f(S) * rho_ref",
                "storage_density": "local pressure-dependent density unchanged",
                "mapback_support": "exact R22 CV-cell support + one same-layer X/Y face-neighbor terminal shell",
                "terminal_support_semantics": "Cartesian occupancy sinks only; never transport CVs or transit nodes",
                "residual_sidecar": "unchanged",
                "stage1_objective": "minimize total terminal-support mass",
                "stage2_objective": "at Stage1 halo optimum, minimize Cartesian cell L1 deviation from represented_parent + direct physical subsegment delta",
                "numerics": {
                    "default_HiGHS_failure_reproduced": True,
                    "repair_solver": "HiGHS dual simplex",
                    "primal_feasibility_tolerance": HIGHS_PRIMAL_FEASIBILITY_TOL,
                    "dual_feasibility_tolerance": HIGHS_DUAL_FEASIBILITY_TOL,
                    "science_CV_equality_gate_kg": MASS_TOL,
                    "science_gate_enlarged": False,
                    "sparse_identity_only": True,
                },
            },
            "frozen_prospective_candidate_sha256": frozen_sha,
            "full_propagation_closed": True,
        }

        decision = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "P2_R6_R29_R3_R2_R1_R1_R1_R2_R1_R1_R1_R3_authorized": True,
            "P2_R6_R29_R3_R2_R1_R1_R1_R2_R1_R1_R1_R3_name": (
                "Controlled Theory-Flux + XY1 Terminal-Support Candidate Execution — No Time Commit"
            ),
            "P2_R6_R29_R3_R2_R1_R1_R1_R2_R1_R1_R1_R3_execution_authorized": True,
            "P2_R6_R29_R3_R2_R1_R1_R1_R2_R1_R1_R1_R3_candidate_only": True,
            "P2_R6_R29_R3_R2_R1_R1_R1_R2_R1_R1_R1_R3_must_bind_frozen_candidate_SHA": frozen_sha,
            "authorized_flux_law": "SG7A_uD_reference_density",
            "XY1_terminal_support_growth_authorized_for_R3": True,
            "absolute_represented_state_reprojection_authorized_for_R3": True,
            "direct_delta_mapback_authorized": False,
            "support_beyond_XY1_authorized": False,
            "residual_sidecar_mutation_authorized": False,
            "nominal_dt_change_authorized": False,
            "inlet_component_flux_change_authorized": False,
            "pressure_refresh_authorized": False,
            "TOF_retrace_authorized": False,
            "storage_density_model_change_authorized": False,
            "CV_capacity_model_change_authorized": False,
            "physical_time_advance_authorized": False,
            "automatic_rerun_authorized": False,
            "R30_authorized": False,
            "P3_authorized": False,
        }

        (out / f"PAD_Stream_{OUT_TOKEN}_Summary.json").write_bytes(jb(summary))
        (out / f"{OUT_TOKEN}_Comprehensive_Repair_Protocol.json").write_bytes(jb(protocol))
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
        print("Intermediate support-audit artifacts   : NOT REQUIRED")
        print("Theory candidate frontier shortfall kg :", frontier_shortfall)
        print("XY1 edge count                         :", nedge)
        print("Stage1 minimum terminal mass kg        :", halo_opt)
        print("Default HiGHS CV equality error kg     :", default_cv_err)
        print("Tight HiGHS CV equality error kg       :", cv_err)
        print("Stage2 terminal mass kg                :", halo2)
        print("Stage2 cell L1 deviation kg            :", L1_exact)
        print("Used terminal edges                    :", summary["stage2_used_terminal_edge_count"])
        print("Cartesian max capacity excess kg       :", cap_excess)
        print("Candidate saturation min/max           :", summary["candidate_saturation_min"], "/", summary["candidate_saturation_max"])
        print("Frozen prospective candidate SHA256    :", frozen_sha)
        print("Dense 37,500 x 37,500 identity         : NOT ALLOCATED")
        print("Controlled execution authorized        : True")
        print("Physical time / R30                    : False / False")
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
