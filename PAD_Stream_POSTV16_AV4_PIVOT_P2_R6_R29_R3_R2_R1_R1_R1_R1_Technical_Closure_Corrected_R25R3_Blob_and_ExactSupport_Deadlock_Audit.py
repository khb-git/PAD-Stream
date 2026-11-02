#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, hashlib, importlib.util, io, json, subprocess, sys, zipfile
from pathlib import Path
from typing import Any
import numpy as np

M = "POSTV16-AV4-PIVOT-P2-R6-R29-R3-R2-R1-R1-R1-R1"
NAME = "Technical Closure: Corrected R25-R3 Blob Authority + Exact-Support Frontier Deadlock + Minimal Terminal Support Extension Audit"

PASS = (
    "AV4PIVOTP2R6R29R3R2R1R1R1R1_TECHNICAL_CLOSURE_CORRECTED_R25R3_BLOB_AND_EXACT_SUPPORT_FRONTIER_DEADLOCK_AND_"
    "MINIMAL_TERMINAL_SUPPORT_EXTENSION_AUDIT_PASS_NO_STATE_MUTATION"
)
BLOCK = "AV4PIVOTP2R6R29R3R2R1R1R1R1_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "20b124f872949e03301d84cc6c9d40cee31f00dd"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"
BASE_AV3 = Path("post_v16") / RID / "POSTV16_AV3_Corey_Relperm_Heterogeneity"

GRID = (15, 50, 50)
NZ, NY, NX = GRID
NCELL = int(np.prod(GRID))
NSL = 1078
NCV = 200
NCVT = NSL * NCV

DT = 0.03721673128859954
TARGET_DAY = 375.0372167312886
BACKGROUND = 0.20
MAX_SAT = 0.80
MASS_TOL = 1.0e-6
SAT_TOL = 1.0e-10
REL_TOL = 1.0e-10

# Latest remap audit authority.
R1_REL = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_R1_R1_"
    "RepresentedState_Remap_Feasibility_and_Full_Propagation_Audit"
)
R1_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_R1_R1_Summary.json"
R1_DECISION = "POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_R1_R1_Decision_Contract.json"
R1_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_R1_R1_Artifact_Manifest.csv"
R1_STATUS = (
    "AV4PIVOTP2R6R29R3R2R1R1_REPRESENTED_STATE_REMAP_FEASIBILITY_AND_"
    "FULL_PROPAGATION_AUDIT_PASS_NO_STATE_MUTATION"
)
R1_CLASS = (
    "THEORY_PREFERRED_FLUX_HAS_NO_FEASIBLE_TESTED_EXISTING_SUPPORT_REMAP_"
    "WITH_FULL_PROPAGATION_CLOSURE"
)

# Flux audit arrays contain theory-preferred transported CV candidate.
F_REL = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_R1_"
    "Compressibility_Accounting_FluxLaw_Alternatives_and_Full_Propagation_Audit"
)
F_ARRAYS = "POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_R1_FluxLaw_Alternative_Propagation_Arrays.npz"
F_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_R1_Artifact_Manifest.csv"

# Accepted Day375 split state.
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

R1_RUNNER = (
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_R1_R1_"
    "RepresentedState_Remap_Feasibility_and_Full_Propagation_Audit.py"
)
R1_RUNNER_BLOB = "f8a8712c0e99394e3ace6347dc9896ab88c94c76"
R25_RUNNER = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R25_R3_Controlled_CapacityLimited_Reprojection_Stage2_PresolveOff.py"
R25_RUNNER_BLOB = "65cab626419137b191f2c53a4c543d9805ccf68d"
R2SRC = "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2SRC_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"
A2E = "PAD_Stream_POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution.py"
A2E_BLOB = "79a8969233b72b4543edd382a0c3d1028c6dca09"


SOURCE_BLOCK_TOKEN = "POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_R1_R1_R1"
SOURCE_BLOCK_REL = BASE / (SOURCE_BLOCK_TOKEN + "_BLOCKED")
SOURCE_BLOCK_FILE = SOURCE_BLOCK_TOKEN + "_Blocked_Report.json"
SOURCE_BLOCK_STATUS = "AV4PIVOTP2R6R29R3R2R1R1R1_TECHNICAL_OR_AUTHORITY_BLOCK"
SOURCE_BLOCK_STAGE = "repository_authority"
SOURCE_BLOCK_EXCEPTION = (
    "GateError('PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R25_R3_"
    "Controlled_CapacityLimited_Reprojection_Stage2_PresolveOff_blob_exact')"
)
SOURCE_BLOCKED_RUNNER = (
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_R1_R1_R1_"
    "ExactSupport_Frontier_Deadlock_and_Minimal_Terminal_Support_Extension_Audit.py"
)
SOURCE_BLOCKED_RUNNER_BLOB = "ca3a6e01e293c5f44b81e3d5b0be7fa5cc67480d"

SOURCE_BLOBS = {
    SOURCE_BLOCKED_RUNNER: SOURCE_BLOCKED_RUNNER_BLOB,
    R1_RUNNER: R1_RUNNER_BLOB,
    R25_RUNNER: R25_RUNNER_BLOB,
    R2SRC: R2SRC_BLOB,
    A2E: A2E_BLOB,
}

OUT_TOKEN = "POSTV16_AV4_PIVOT_P2_R6_R29_R3_R2_R1_R1_R1_R1"
OUT_REL = BASE / (
    OUT_TOKEN + "_Technical_Closure_Corrected_R25R3_Blob_and_ExactSupport_Deadlock_Audit"
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


def npzb(arrays: dict[str, Any]) -> bytes:
    outer = io.BytesIO()
    with zipfile.ZipFile(outer, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for key in sorted(arrays):
            arr = np.asarray(arrays[key])
            if arr.dtype == object:
                raise GateError(f"object_dtype:{key}")
            payload = io.BytesIO()
            np.lib.format.write_array(payload, arr, allow_pickle=False)
            info = zipfile.ZipInfo(f"{key}.npy")
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            zf.writestr(info, payload.getvalue())
    return outer.getvalue()


def unravel_cell(c: int) -> tuple[int, int, int]:
    k = c // (NY * NX)
    rem = c % (NY * NX)
    j = rem // NX
    i = rem % NX
    return int(k), int(j), int(i)


def flat_cell(k: int, j: int, i: int) -> int:
    return int((k * NY + j) * NX + i)


def topology_cells(cell: int, mode: str) -> list[tuple[int, int]]:
    """Return (flat_cell, shell_cost), including original cell at cost 0."""
    k, j, i = unravel_cell(int(cell))
    out = {(cell, 0)}
    if mode == "EXACT":
        return list(out)

    if mode in ("XY1", "XYZ1", "XY2"):
        for dj, di in ((-1,0),(1,0),(0,-1),(0,1)):
            jj, ii = j + dj, i + di
            if 0 <= jj < NY and 0 <= ii < NX:
                out.add((flat_cell(k,jj,ii), 1))

    if mode == "XYZ1":
        for dk in (-1,1):
            kk = k + dk
            if 0 <= kk < NZ:
                out.add((flat_cell(kk,j,i), 1))

    if mode == "XY2":
        for dj in range(-2,3):
            for di in range(-2,3):
                d = abs(dj) + abs(di)
                if d != 2:
                    continue
                jj, ii = j + dj, i + di
                if 0 <= jj < NY and 0 <= ii < NX:
                    out.add((flat_cell(k,jj,ii), 2))

    return list(out)


def build_extended_support(edge_cv: np.ndarray, edge_cell: np.ndarray, mode: str):
    pairs = {}
    for cv, cell in zip(edge_cv.tolist(), edge_cell.tolist()):
        for c2, cost in topology_cells(int(cell), mode):
            key = int(cv) * NCELL + int(c2)
            old = pairs.get(key)
            if old is None or cost < old:
                pairs[key] = int(cost)
    keys = np.fromiter(pairs.keys(), dtype=np.int64)
    order = np.argsort(keys)
    keys = keys[order]
    costs = np.asarray([pairs[int(k)] for k in keys], dtype=np.int8)
    return (keys // NCELL).astype(np.int64), (keys % NCELL).astype(np.int64), costs


def selftest() -> None:
    c = flat_cell(2, 10, 10)
    assert len(topology_cells(c, "EXACT")) == 1
    assert len(topology_cells(c, "XY1")) == 5
    assert len(topology_cells(c, "XYZ1")) == 7
    assert len(topology_cells(c, "XY2")) == 13
    print("POSTV16 AV4 PIVOT P2-R6-R29-R3-R2-R1-R1-R1-R1 structural self-test: PASS")


def main(project_root: Path, drive_root: Path) -> int:
    from scipy.optimize import linprog
    from scipy.sparse import coo_matrix

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
        gate("parent_exact", gt(root, "rev-parse", "HEAD^") == PARENT)
        gate("repository_clean", gt(root, "status", "--porcelain") == "")
        for fn, expected in SOURCE_BLOBS.items():
            p = root / fn
            gate(f"{Path(fn).stem}_present", p.is_file(), str(p))
            actual = gt(root, "hash-object", str(p)) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_blob_exact", actual == expected, actual)

        stage = "immutable_source_BLOCK_authority"
        source_block_path = drive / SOURCE_BLOCK_REL / SOURCE_BLOCK_FILE
        gate("source_BLOCK_exists", source_block_path.is_file(), str(source_block_path))
        source_block = js(source_block_path)
        source_block_sha = sha(source_block_path)
        gate("source_BLOCK_status_exact", source_block.get("status") == SOURCE_BLOCK_STATUS, source_block.get("status"))
        gate("source_BLOCK_failed_stage_exact", source_block.get("failed_stage") == SOURCE_BLOCK_STAGE, source_block.get("failed_stage"))
        gate("source_BLOCK_exception_exact", source_block.get("exception") == SOURCE_BLOCK_EXCEPTION, source_block.get("exception"))
        gate("source_BLOCK_no_state_mutation", source_block.get("state_mutation_executed") is False)
        gate("source_BLOCK_no_support_growth", source_block.get("support_growth_executed") is False)
        gate("source_BLOCK_no_time_advance", source_block.get("physical_time_advance_executed") is False)

        stage = "latest_remap_audit_authority"
        r1 = drive / R1_REL
        mm1 = manifest(r1, R1_MANIFEST)
        s1 = js(r1 / R1_SUMMARY)
        d1 = js(r1 / R1_DECISION)
        gate("R1_status_exact", s1.get("status") == R1_STATUS, s1.get("status"))
        gate("R1_classification_exact", s1.get("classification") == R1_CLASS, s1.get("classification"))
        gate("R1_no_preferred_mapback", s1.get("preferred_mapback_family") is None)
        gate("R1_next_design_not_authorized", d1.get("P2_R6_R29_R3_R2_R1_R2_authorized") is False)
        gate("R1_support_growth_not_authorized", d1.get("support_growth_authorized") is False)

        stage = "accepted_parent_authority"
        r25 = drive / R25_REL
        m25 = manifest(r25, R25_MANIFEST)
        sp = r25 / R25_STATE
        gate("R25_state_SHA", m25.get(R25_STATE) == R25_SHA and sha(sp) == R25_SHA)
        with np.load(sp, allow_pickle=False) as z:
            grid_parent = np.asarray(z["cartesian_component_mass_kg"], dtype=np.float64)
            represented_parent = np.asarray(z["represented_cartesian_cell_mass_kg"], dtype=np.float64)
            residual_parent = np.asarray(z["grid_residual_component_mass_kg"], dtype=np.float64)
            old_cv_mass = np.asarray(z["transport_CV_component_mass_kg"], dtype=np.float64)
            edge_cv_exact = np.asarray(z["exact_support_edge_cv"], dtype=np.int64)
            edge_cell_exact = np.asarray(z["exact_support_edge_cell"], dtype=np.int64)
            edge_x_parent = np.asarray(z["exact_support_edge_assigned_mass_kg"], dtype=np.float64)
            stage1_frontier = float(np.asarray(z["stage1_maximum_representable_mass_kg"]).reshape(()))
            pressure = np.asarray(z["refreshed_pressure_psi"], dtype=np.float64)
            p_ref = float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))

        parent_rep_total = float(np.sum(represented_parent))
        parent_cv_total = float(np.sum(old_cv_mass))
        frontier_gap = stage1_frontier - parent_rep_total
        gate("R25_parent_at_exact_support_frontier", abs(frontier_gap) <= 1e-6, frontier_gap)
        gate("R25_parent_rep_equals_CV_total", abs(parent_rep_total - parent_cv_total) <= 1e-6,
             parent_rep_total - parent_cv_total)
        gate("R25_edge_assignment_total_matches_parent", abs(float(np.sum(edge_x_parent)) - parent_rep_total) <= 1e-6)

        stage = "theory_transport_candidate_authority"
        fd = drive / F_REL
        mmf = manifest(fd, F_MANIFEST)
        gate("flux_arrays_manifested", F_ARRAYS in mmf)
        with np.load(fd / F_ARRAYS, allow_pickle=False) as z:
            new_cv_mass = np.asarray(z["SG7A_uD_reference_density_new_CV_mass_kg"], dtype=np.float64)
            theory_flux = np.asarray(z["SG7A_uD_reference_density_face_mass_flux_kg_day"], dtype=np.float64)

        new_cv_total = float(np.sum(new_cv_mass))
        net_positive_increment = new_cv_total - parent_cv_total
        gate("theory_transport_net_storage_positive", net_positive_increment > 0.0, net_positive_increment)
        exact_frontier_shortfall = new_cv_total - stage1_frontier
        gate("theory_candidate_exceeds_exact_support_frontier", exact_frontier_shortfall > 0.0, exact_frontier_shortfall)

        stage = "heterogeneous_cartesian_capacity"
        r2src = load_module(root / R2SRC, "supportaudit_r2")
        a2e = load_module(root / A2E, "supportaudit_a2e")
        a6 = drive / A6E_REL / A6E_STATE
        gate("A6E_SHA", a6.is_file() and sha(a6) == A6E_SHA)
        with np.load(a6, allow_pickle=False) as z:
            phi = np.asarray(z["paired_porosity"], dtype=np.float64)
        hetero_pv = phi * float(a2e.BULK_VOLUME_M3)
        full_sat = np.full(GRID, float(a2e.INJECTED), dtype=np.float64)
        cart_capacity = np.asarray(
            a2e.local_mass(r2src, full_sat, pressure, p_ref, hetero_pv),
            dtype=np.float64,
        )
        represented_capacity = cart_capacity - residual_parent
        cap_tol = max(1e-8, 1e-12 * max(float(np.max(cart_capacity)), 1.0))
        gate("represented_capacity_nonnegative", float(np.min(represented_capacity)) >= -cap_tol,
             float(np.min(represented_capacity)))
        represented_capacity = np.maximum(represented_capacity, 0.0)

        # Terminal-support extension families.
        stage = "support_topology_feasibility"
        topology_order = ("EXACT", "XY1", "XYZ1", "XY2")
        topology_results = {}
        arrays = {
            "exact_support_edge_cv": edge_cv_exact,
            "exact_support_edge_cell": edge_cell_exact,
            "parent_exact_edge_assignment_kg": edge_x_parent,
            "theory_new_CV_mass_kg": new_cv_mass,
            "represented_capacity_kg": represented_capacity,
        }

        flat_cap = represented_capacity.reshape(-1)
        active_cvs = np.where(new_cv_mass.reshape(-1) > MASS_TOL)[0]
        cv_row_map = np.full(NCVT, -1, dtype=np.int64)
        cv_row_map[active_cvs] = np.arange(len(active_cvs), dtype=np.int64)
        b_eq = new_cv_mass.reshape(-1)[active_cvs]

        first_feasible = None

        for mode in topology_order:
            print(f"--- SUPPORT TOPOLOGY {mode} ---")
            ecv, ecell, shell = build_extended_support(edge_cv_exact, edge_cell_exact, mode)
            nedge = len(ecv)

            rr = cv_row_map[ecv]
            mask = rr >= 0
            eq_cols = np.nonzero(mask)[0]
            Aeq = coo_matrix(
                (
                    np.ones(len(eq_cols), dtype=np.float64),
                    (rr[mask], eq_cols),
                ),
                shape=(len(active_cvs), nedge),
            ).tocsr()

            A_cell = coo_matrix(
                (
                    np.ones(nedge, dtype=np.float64),
                    (ecell, np.arange(nedge, dtype=np.int64)),
                ),
                shape=(NCELL, nedge),
            ).tocsr()

            # Primary objective: minimize mass assigned outside exact support.
            c = (shell > 0).astype(np.float64)
            lp = linprog(
                c,
                A_ub=A_cell,
                b_ub=flat_cap,
                A_eq=Aeq,
                b_eq=b_eq,
                bounds=(0.0, None),
                method="highs",
                options={"presolve": True},
            )

            feasible = bool(lp.success)
            result = {
                "topology": mode,
                "edge_count": int(nedge),
                "active_CV_count": int(len(active_cvs)),
                "LP_feasible": feasible,
                "LP_status": int(lp.status),
                "LP_message": str(lp.message),
                "terminal_extension_only": mode != "EXACT",
                "transport_operator_changed": False,
                "CV_state_changed": False,
                "residual_sidecar_changed": False,
            }

            if feasible:
                x = np.asarray(lp.x, dtype=np.float64)
                rep = np.bincount(ecell, weights=x, minlength=NCELL).reshape(GRID)
                candidate = rep + residual_parent

                cv_check = np.bincount(ecv, weights=x, minlength=NCVT).reshape(NSL, NCV)
                cv_err = float(np.max(np.abs(cv_check - new_cv_mass)))
                cell_excess = float(np.max(candidate - cart_capacity))
                min_rep = float(np.min(rep))
                split_err = float(np.max(np.abs(candidate - rep - residual_parent)))

                halo_mass = float(np.sum(x[shell > 0]))
                shell1_mass = float(np.sum(x[shell == 1]))
                shell2_mass = float(np.sum(x[shell == 2]))
                used_halo_edges = int(np.count_nonzero((shell > 0) & (x > MASS_TOL)))

                injected = float(np.sum(theory_flux[:, 0]) * DT)
                produced = float(np.sum(theory_flux[:, -1]) * DT)
                target_total = float(np.sum(grid_parent)) + injected - produced
                source_sink_residual = float(np.sum(candidate)) - target_total
                global_tol = max(MASS_TOL, REL_TOL * max(abs(target_total), 1.0))

                candidate_sg = np.asarray(
                    a2e.invert_local_mass(
                        r2src,
                        candidate,
                        pressure,
                        p_ref,
                        hetero_pv,
                    ),
                    dtype=np.float64,
                )
                candidate_sat = float(a2e.BACKGROUND) + candidate_sg
                reconstructed = np.asarray(
                    a2e.local_mass(
                        r2src,
                        candidate_sat,
                        pressure,
                        p_ref,
                        hetero_pv,
                    ),
                    dtype=np.float64,
                )
                recon_err = float(np.max(np.abs(reconstructed - candidate)))

                downstream_pass = (
                    cv_err <= MASS_TOL
                    and cell_excess <= cap_tol
                    and min_rep >= -MASS_TOL
                    and split_err <= MASS_TOL
                    and abs(source_sink_residual) <= global_tol
                    and recon_err <= 1e-8
                    and float(np.min(candidate_sat)) >= BACKGROUND - SAT_TOL
                    and float(np.max(candidate_sat)) <= MAX_SAT + SAT_TOL
                )

                result.update({
                    "minimum_terminal_extension_mass_kg": halo_mass,
                    "shell1_terminal_mass_kg": shell1_mass,
                    "shell2_terminal_mass_kg": shell2_mass,
                    "used_terminal_extension_edge_count": used_halo_edges,
                    "CV_equality_max_abs_error_kg": cv_err,
                    "minimum_represented_mass_kg": min_rep,
                    "cartesian_max_capacity_excess_kg": cell_excess,
                    "split_identity_max_abs_error_kg": split_err,
                    "cartesian_source_sink_residual_kg": source_sink_residual,
                    "cartesian_mass_reconstruction_max_abs_error_kg": recon_err,
                    "candidate_saturation_min": float(np.min(candidate_sat)),
                    "candidate_saturation_max": float(np.max(candidate_sat)),
                    "full_downstream_propagation_pass": bool(downstream_pass),
                })

                arrays[f"{mode}_edge_cv"] = ecv
                arrays[f"{mode}_edge_cell"] = ecell
                arrays[f"{mode}_edge_shell_cost"] = shell
                arrays[f"{mode}_edge_allocation_kg"] = x
                arrays[f"{mode}_represented_candidate_kg"] = rep
                arrays[f"{mode}_candidate_grid_mass_kg"] = candidate

                if first_feasible is None and downstream_pass:
                    first_feasible = mode
            else:
                result.update({
                    "minimum_terminal_extension_mass_kg": None,
                    "full_downstream_propagation_pass": False,
                })

            topology_results[mode] = result
            print(mode, result)

        if first_feasible is None:
            classification = (
                "EXACT_SUPPORT_FRONTIER_DEADLOCK_CONFIRMED_AND_NO_TESTED_TERMINAL_"
                "SUPPORT_EXTENSION_TOPOLOGY_ACHIEVES_FULL_PROPAGATION_CLOSURE"
            )
        elif first_feasible == "XY1":
            classification = (
                "EXACT_SUPPORT_FRONTIER_DEADLOCK_CONFIRMED_ONE_SHELL_SAME_LAYER_XY_"
                "TERMINAL_SUPPORT_EXTENSION_IS_MINIMAL_TESTED_FULL_CLOSURE_TOPOLOGY"
            )
        elif first_feasible == "XYZ1":
            classification = (
                "EXACT_SUPPORT_FRONTIER_DEADLOCK_CONFIRMED_FULL_FACE_NEIGHBOR_"
                "ONE_SHELL_TERMINAL_SUPPORT_EXTENSION_REQUIRED_FOR_FULL_CLOSURE"
            )
        else:
            classification = (
                "EXACT_SUPPORT_FRONTIER_DEADLOCK_CONFIRMED_TWO_SHELL_SAME_LAYER_XY_"
                "TERMINAL_SUPPORT_EXTENSION_REQUIRED_FOR_FULL_CLOSURE"
            )

        stage = "publication"
        out.mkdir(parents=True, exist_ok=False)
        (out / f"{OUT_TOKEN}_Support_Topology_Feasibility_Arrays.npz").write_bytes(npzb(arrays))

        rows = []
        for mode in topology_order:
            r = topology_results[mode]
            rows.append({
                "topology": mode,
                "edge_count": r["edge_count"],
                "LP_feasible": r["LP_feasible"],
                "minimum_terminal_extension_mass_kg": r.get("minimum_terminal_extension_mass_kg"),
                "shell1_terminal_mass_kg": r.get("shell1_terminal_mass_kg"),
                "shell2_terminal_mass_kg": r.get("shell2_terminal_mass_kg"),
                "used_terminal_extension_edge_count": r.get("used_terminal_extension_edge_count"),
                "full_downstream_propagation_pass": r["full_downstream_propagation_pass"],
                "LP_status": r["LP_status"],
                "LP_message": r["LP_message"],
            })
        (out / f"{OUT_TOKEN}_Support_Topology_Comparison.csv").write_bytes(csvb(rows))

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": classification,
            "source_R29R3R2R1R1R1_BLOCK_sha256": source_block_sha,
            "source_R29R3R2R1R1_summary_sha256": mm1[R1_SUMMARY],
            "nominal_dt_days": DT,
            "candidate_target_day": TARGET_DAY,
            "R25_stage1_exact_support_frontier_kg": stage1_frontier,
            "R25_parent_represented_total_kg": parent_rep_total,
            "R25_parent_CV_total_kg": parent_cv_total,
            "R25_parent_frontier_gap_kg": frontier_gap,
            "theory_transport_candidate_CV_total_kg": new_cv_total,
            "theory_transport_net_positive_storage_kg": net_positive_increment,
            "theory_candidate_exact_support_frontier_shortfall_kg": exact_frontier_shortfall,
            "structural_deadlock_proved": bool(
                abs(frontier_gap) <= 1e-6 and exact_frontier_shortfall > MASS_TOL
            ),
            "tested_topology_order": list(topology_order),
            "first_full_closure_topology": first_feasible,
            "topology_results": topology_results,
            "state_mutation_executed": False,
            "support_growth_executed": False,
            "physical_time_advance_executed": False,
            "R30_authorized": False,
            "P3_authorized": False,
        }

        audit = {
            "milestone": M,
            "status": PASS,
            "technical_closure": "corrects only the historical R25-R3 Git blob authority binding from the immutable parent BLOCK; the scientific topology audit is unchanged",
            "scientific_conclusion": (
                "R25-R3 placed the accepted Day375 represented state on the exact-support "
                "maximum-representable frontier. Therefore any positive-net-storage transport "
                "candidate is mathematically incompatible with exact support + fixed residual."
            ),
            "escape_families_considered": {
                "exact_support": "baseline; no support extension",
                "XY1": "one same-layer Cartesian X/Y face-neighbor terminal occupancy shell",
                "XYZ1": "one Cartesian X/Y/Z face-neighbor terminal occupancy shell",
                "XY2": "same-layer Manhattan-distance <=2 terminal occupancy extension",
            },
            "terminal_semantics": (
                "extension cells are Cartesian mapback occupancy sinks only; they are not "
                "transport CVs, transit nodes, streamline retraces, or pressure/TOF changes"
            ),
            "topology_results": topology_results,
        }

        design_authorized = first_feasible is not None
        decision = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "P2_R6_R29_R3_R2_R1_R1_R1_R2_authorized": bool(design_authorized),
            "P2_R6_R29_R3_R2_R1_R1_R1_R2_name": (
                "Comprehensive Theory-Flux + Minimal Terminal-Support Mapback Repair Design Freeze"
            ),
            "P2_R6_R29_R3_R2_R1_R1_R1_R2_design_only": True,
            "P2_R6_R29_R3_R2_R1_R1_R1_R2_execution_authorized": False,
            "preferred_flux_law": "SG7A_uD_reference_density" if design_authorized else None,
            "minimal_tested_terminal_support_topology": first_feasible,
            "terminal_support_growth_design_may_be_considered": bool(design_authorized),
            "support_growth_executed": False,
            "transport_operator_change_authorized": False,
            "pressure_refresh_authorized": False,
            "TOF_retrace_authorized": False,
            "residual_sidecar_mutation_authorized": False,
            "nominal_dt_change_authorized": False,
            "inlet_component_flux_change_authorized": False,
            "storage_density_model_change_authorized": False,
            "CV_capacity_model_change_authorized": False,
            "physical_time_advance_authorized": False,
            "R30_authorized": False,
            "P3_authorized": False,
        }

        (out / f"PAD_Stream_{OUT_TOKEN}_Summary.json").write_bytes(jb(summary))
        (out / f"{OUT_TOKEN}_ExactSupport_Deadlock_and_TerminalSupport_Audit.json").write_bytes(jb(audit))
        (out / f"{OUT_TOKEN}_Decision_Contract.json").write_bytes(jb(decision))
        (out / f"{OUT_TOKEN}_Final_Gate_Matrix.csv").write_bytes(csvb(gates))

        mrows = []
        for p in sorted(out.iterdir()):
            if p.is_file():
                mrows.append({"file": p.name, "sha256": sha(p), "bytes": p.stat().st_size})
        (out / f"{OUT_TOKEN}_Artifact_Manifest.csv").write_bytes(csvb(mrows))

        print("=" * 200)
        print(M, "PASS")
        print("Classification                               :", classification)
        print("R25 exact-support frontier kg               :", stage1_frontier)
        print("Parent represented total kg                 :", parent_rep_total)
        print("Theory candidate CV total kg                :", new_cv_total)
        print("Net positive storage kg                     :", net_positive_increment)
        print("Exact-support frontier shortfall kg         :", exact_frontier_shortfall)
        print("Structural exact-support deadlock proved    :", summary["structural_deadlock_proved"])
        print("First full-closure topology                 :", first_feasible)
        for mode in topology_order:
            r = topology_results[mode]
            print(
                f"{mode:8s} edges={r['edge_count']} feasible={r['LP_feasible']} "
                f"terminal_mass_kg={r.get('minimum_terminal_extension_mass_kg')} "
                f"full_closure={r['full_downstream_propagation_pass']}"
            )
        print("Next design freeze authorized               :", design_authorized)
        print("State / support growth / time / R30         : False / False / False / False")
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
                "source_parent_BLOCK_preserved": True,
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
