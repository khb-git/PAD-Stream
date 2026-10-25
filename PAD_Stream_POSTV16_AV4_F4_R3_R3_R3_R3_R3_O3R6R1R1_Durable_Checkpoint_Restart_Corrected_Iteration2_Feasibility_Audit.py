#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import gc
import hashlib
import importlib.util
import io
import json
import math
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any

import numpy as np

MILESTONE = "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R6-R1-R1"
STATUS_PASS = (
    "AV4F4R3R3R3R3R3O3R6R1R1_DURABLE_CHECKPOINT_RESTART_CORRECTED_"
    "ITERATION2_FROZEN_E2_EXACT_FEASIBILITY_RECERTIFICATION_AUDIT_PASS_"
    "NO_COUPLED_CONTINUATION_NO_TIME_ADVANCE"
)
STATUS_BLOCK = "AV4F4R3R3R3R3R3O3R6R1R1_TECHNICAL_OR_AUTHORITY_BLOCK"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT_O3R6R1_COMMIT = "6121fa2d43d02d394f96f841559206b2adb0fe5a"
EVENT_DAY = 413.78677770818403
GRID = (15, 50, 50)
NCELL = 37500
NSL = 1078
NCV = 200
NCVTOTAL = 215600
BACKGROUND = 0.20
INJECTED = 0.80
EXPECTED_E0 = 269721
EXPECTED_E2 = 3091073
EXPECTED_ACTIVE = 3012452
NUM_ZERO = 1.0e-6

O3R6R1 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R1_"
    "Iteration2_FrozenE2_Exact_Feasibility_Recertification_Audit.py"
)
O3R6R1_BLOB = "98cc5c1f8d295260cf0571b287a0a4c54716db56"
O3R6 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6_"
    "Controlled_Coupled_Pressure_SameH2_Reassignment_Fixed_Point_Execution.py"
)
O3R6_BLOB = "368cfa24dd395e3e07df033c9ed95ab4024a3a4b"
O3R6_FAIL_STATUS = (
    "AV4F4R3R3R3R3R3O3R6_COUPLED_PRESSURE_SAME_H2_REASSIGNMENT_"
    "FIXED_POINT_SCIENTIFIC_FAIL_NO_DAMPING_NO_SUPPORT_EXPANSION_NO_AUTOMATIC_RERUN"
)
O3R4 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R4_"
    "Exact_Frozen_E2_First_Refresh_Capacity_Feasibility_Audit.py"
)
O3R4_BLOB = "4446ca612d1f6a00472327818aff674d568f9ede"
O2 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O2_"
    "Persistent_Native_HiGHS_H2_Assignment_Execution.py"
)
O2_BLOB = "2e04f77750add23f9cfe5143119668450201354f"
A2E = "PAD_Stream_POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution.py"
A2E_BLOB = "79a8969233b72b4543edd382a0c3d1028c6dca09"
R2PHYS = (
    "PAD_Stream_V16E35_R2_Source_Conservative_Transport_"
    "Capillary_Split_First_Controlled_Transition.py"
)
R2PHYS_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"
SG2 = "PAD_Stream_V15SG2_Anisotropic_Transmissibility.py"
SG2_BLOB = "7242012d3e758472abc3ee7f543831b92d2cf419"
SG3 = "PAD_Stream_V15SG3_FiveSpot_Pressure_Solve.py"
SG3_BLOB = "66a379cd97ee9120f69e7e7e949171541e4918c3"
R3R2R1 = "PAD_Stream_V16E41R3R2R1_Local_Conservation_Sign_Convention_Repair.py"
R3R2R1_BLOB = "740c6da03e73906646bf0153633187e749449f31"
PERM = "SGSIM_50x50x15_PERM_MD.csv"
PERM_BLOB = "317dd47d458bc6f880c2e3dc4ec1f69eeb0dd314"

SOURCES = {
    O3R6R1: O3R6R1_BLOB,
    O3R6: O3R6_BLOB,
    O3R4: O3R4_BLOB,
    O2: O2_BLOB,
    A2E: A2E_BLOB,
    R2PHYS: R2PHYS_BLOB,
    SG2: SG2_BLOB,
    SG3: SG3_BLOB,
    R3R2R1: R3R2R1_BLOB,
    PERM: PERM_BLOB,
}

BASE = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"
O2_REL = BASE / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O2_Persistent_Native_HiGHS_H2_Assignment_Execution"
O2_STATE = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O2_Optimized_Event_MapBack_State.npz"
O2_MANIFEST = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O2_Artifact_Manifest.csv"
A2E_REL = BASE / "POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution"
A2E_EPOCH = "POSTV16_AV4_A2_E_Refreshed_Flow_Epoch.npz"
A2E_MANIFEST = "POSTV16_AV4_A2_E_Artifact_Manifest.csv"

FAIL_REL = BASE / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6_SCIENTIFIC_FAIL"
FAIL_REPORT = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6_Scientific_Fail_Report.json"
FAIL_NONLIN = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6_Fail_Nonlinear_Telemetry.csv"
FAIL_ASSIGN = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6_Fail_Assignment_Telemetry.csv"

OUT_REL = BASE / (
    "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R1R1_"
    "Durable_Checkpoint_Restart_Corrected_Iteration2_Feasibility_Audit"
)
CHECKPOINT_REL = BASE / (
    "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R1R1_Durable_Checkpoints"
)
BLOCK_REL = BASE / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R1R1_BLOCKED"

CP1_STATE = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R1R1_Iteration001_Certified_State.npz"
CP1_META = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R1R1_Iteration001_Certified_State.json"
CP1_MANIFEST = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R1R1_Iteration001_Checkpoint_Manifest.csv"
CP2_STATE = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R1R1_P2_Diagnostic_State.npz"
CP2_META = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R1R1_P2_Diagnostic_State.json"
CP2_MANIFEST = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R1R1_P2_Checkpoint_Manifest.csv"


class GateError(RuntimeError):
    pass


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError("cannot_load_module:" + str(path))
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def git_text(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True, text=True, capture_output=True
    ).stdout.strip()


def git_blob(path: Path, root: Path) -> str:
    return git_text(root, "hash-object", str(path))


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def load_json(p: Path) -> dict[str, Any]:
    return json.loads(p.read_text(encoding="utf-8"))


def read_csv(p: Path) -> list[dict[str, str]]:
    with p.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def verify_manifest(d: Path, n: str) -> dict[str, str]:
    p = d / n
    if not p.is_file():
        raise GateError("manifest_missing:" + str(p))
    rows = read_csv(p)
    if not rows:
        raise GateError("manifest_empty:" + n)
    out = {}
    for r in rows:
        fp = d / r["file"]
        if not fp.is_file():
            raise GateError("manifest_payload_missing:" + r["file"])
        actual = sha256_file(fp)
        if actual != r["sha256"]:
            raise GateError("manifest_sha_mismatch:" + r["file"])
        out[r["file"]] = actual
    return out


def json_bytes(o: Any) -> bytes:
    return (json.dumps(o, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def csv_bytes(rows: list[dict[str, Any]]) -> bytes:
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
    return s.getvalue().encode("utf-8")


def deterministic_npz_bytes(arrays: dict[str, Any]) -> bytes:
    outer = io.BytesIO()
    with zipfile.ZipFile(
        outer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as z:
        for k in sorted(arrays):
            b = io.BytesIO()
            np.save(b, np.asarray(arrays[k]), allow_pickle=False)
            info = zipfile.ZipInfo(k + ".npy", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            z.writestr(info, b.getvalue())
    return outer.getvalue()


def immutable_publish(out: Path, files: dict[str, bytes]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for n, d in files.items():
        p = out / n
        if p.exists() and p.read_bytes() != d:
            raise GateError("existing_output_differs:" + n)
        if not p.exists():
            p.write_bytes(d)


def publish_checkpoint(checkpoint_dir: Path, state_name: str, state_bytes: bytes,
                       meta_name: str, meta_bytes: bytes, manifest_name: str) -> None:
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    state_path = checkpoint_dir / state_name
    meta_path = checkpoint_dir / meta_name

    if state_path.exists() and state_path.read_bytes() != state_bytes:
        raise GateError("checkpoint_state_conflict:" + state_name)
    if meta_path.exists() and meta_path.read_bytes() != meta_bytes:
        raise GateError("checkpoint_metadata_conflict:" + meta_name)
    if not state_path.exists():
        state_path.write_bytes(state_bytes)
    if not meta_path.exists():
        meta_path.write_bytes(meta_bytes)

    rows = [
        {"file": state_name, "sha256": sha256_file(state_path), "bytes": state_path.stat().st_size},
        {"file": meta_name, "sha256": sha256_file(meta_path), "bytes": meta_path.stat().st_size},
    ]
    manifest_bytes = csv_bytes(rows)
    manifest_path = checkpoint_dir / manifest_name
    if manifest_path.exists() and manifest_path.read_bytes() != manifest_bytes:
        raise GateError("checkpoint_manifest_conflict:" + manifest_name)
    if not manifest_path.exists():
        manifest_path.write_bytes(manifest_bytes)


def checkpoint_valid(checkpoint_dir: Path, manifest_name: str, expected_files: set[str]) -> bool:
    if not checkpoint_dir.is_dir() or not (checkpoint_dir / manifest_name).is_file():
        return False
    try:
        m = verify_manifest(checkpoint_dir, manifest_name)
        return set(m) == expected_files
    except Exception:
        return False


def fsum(a: np.ndarray) -> float:
    return float(math.fsum(float(x) for x in np.asarray(a, dtype=np.float64).ravel()))


def max_abs(a: np.ndarray) -> float:
    return float(np.max(np.abs(np.asarray(a, dtype=np.float64))))


def relative_l2(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    return float(np.linalg.norm((a - b).ravel()) / max(float(np.linalg.norm(b.ravel())), 1.0e-30))


def self_test() -> None:
    assert MILESTONE.endswith("O3-R6-R1-R1")
    assert NCVTOTAL == 215600
    assert EXPECTED_ACTIVE == 3012452
    assert len(PARENT_O3R6R1_COMMIT) == 40
    print("POSTV16 O3-R6-R1-R1 durable checkpoint/restart correction structural self-test: PASS")


def main(project_root: Path, drive_root: Path, verbose_solver: bool = False) -> int:
    root = Path(project_root).resolve()
    drive = Path(drive_root).resolve()
    out = drive / OUT_REL
    checkpoints = drive / CHECKPOINT_REL
    blocked = drive / BLOCK_REL
    gates: dict[str, dict[str, Any]] = {}
    stage = "preflight"
    solvers = []
    rec_rows: list[dict[str, Any]] = []
    checkpoint_iteration1_reused = False
    checkpoint_p2_reused = False

    def gate(n: str, c: bool, d: Any = None) -> None:
        gates[n] = {"status": "PASS" if c else "FAIL", "detail": d}
        if not c:
            raise GateError(f"{n}: {d!r}")
        print(f"[PASS] {n}" + (f" -- {d}" if d is not None else ""))

    print("=" * 208)
    print(MILESTONE + " -- DURABLE CHECKPOINT/RESTART CORRECTED ITERATION-2 FROZEN-E2 EXACT FEASIBILITY AUDIT")
    print("=" * 208)
    print("O3-R6-R1 REMAINS IMMUTABLE. THIS RUNNER CHANGES CHECKPOINT/RESTART BEHAVIOR ONLY.")
    print("SCIENTIFIC AUDIT SEMANTICS ARE UNCHANGED.")
    print("CERTIFIED ITERATION-1 STATE IS WRITTEN BEFORE P2 WORK; P2 STATE IS WRITTEN BEFORE THE MIN-UNSERVED LP.")
    print("ON RERUN, VALID CHECKPOINTS ARE VERIFIED AND REUSED; EXPENSIVE COMPLETED WORK IS NOT REPEATED.")
    print("NO COUPLED CONTINUATION. NO DAMPING. NO SUPPORT EXPANSION. NO DARCY/POLLOCK/TOF. NO TIME ADVANCE.")
    print()

    try:
        stage = "repository_authority"
        parent = git_text(root, "rev-parse", "HEAD^")
        status = git_text(root, "status", "--porcelain")
        gate("repository_parent_is_O3R6R1_commit", parent == PARENT_O3R6R1_COMMIT, parent)
        gate("repository_clean", status == "", repr(status))
        for fn, exp in SOURCES.items():
            p = root / fn
            actual = git_blob(p, root) if p.is_file() else "missing"
            gate(Path(fn).stem + "_git_blob_exact", actual == exp, actual)

        o3r6 = load_module(root / O3R6, "postv16_o3r6r1r1_parent_o3r6")
        o3r4 = load_module(root / O3R4, "postv16_o3r6r1r1_r4")
        o2 = load_module(root / O2, "postv16_o3r6r1r1_o2")
        a2e = load_module(root / A2E, "postv16_o3r6r1r1_a2e")
        r2 = load_module(root / R2PHYS, "postv16_o3r6r1r1_r2")
        sg2 = load_module(root / SG2, "postv16_o3r6r1r1_sg2")
        sg3 = load_module(root / SG3, "postv16_o3r6r1r1_sg3")
        r3r2r1 = load_module(root / R3R2R1, "postv16_o3r6r1r1_r3r2r1")

        import highspy
        from scipy.sparse import coo_matrix
        gate("highspy_version_exact_1_15_1", highspy.Highs().version() == "1.15.1", highspy.Highs().version())

        stage = "O3R6_fail_binding"
        fd = drive / FAIL_REL
        gate("O3R6_fail_directory_present", fd.is_dir(), str(fd))
        fr = load_json(fd / FAIL_REPORT)
        gate(
            "O3R6_fail_exact",
            fr.get("status") == O3R6_FAIL_STATUS
            and fr.get("failed_gate") == "frozen_E2_lexicographic_assignment_infeasible"
            and int(fr.get("current_iteration", -1)) == 2
            and int(fr.get("detail", {}).get("iteration", -1)) == 2
            and int(fr.get("detail", {}).get("stage", -1)) == 1
            and fr.get("detail", {}).get("model_status") == "Infeasible"
            and fr.get("automatic_rerun_authorized") is False
            and fr.get("physical_time_advanced") is False,
            fr.get("detail"),
        )
        nonlin_fail = read_csv(fd / FAIL_NONLIN)
        assign_fail = read_csv(fd / FAIL_ASSIGN)
        gate("O3R6_fail_contains_exactly_one_completed_nonlinear_iteration", len(nonlin_fail) == 1, [r.get("iteration") for r in nonlin_fail])
        gate("O3R6_fail_contains_five_iteration1_assignment_stages", len([r for r in assign_fail if int(r["nonlinear_iteration"]) == 1]) == 5, len(assign_fail))

        obj_keys = ["stage1_shell_kg", "stage2_extension_kg", "stage3_parent_L1_kg", "stage4_raw_L1_kg", "stage5_tiebreak"]
        original_obj = {k: float(nonlin_fail[0][k]) for k in obj_keys}

        stage = "state_binding"
        o2d = drive / O2_REL
        verify_manifest(o2d, O2_MANIFEST)
        with np.load(o2d / O2_STATE, allow_pickle=False) as z:
            event_grid0 = np.asarray(z["event_grid_component_mass_kg"], float)
            residual_grid = np.asarray(z["frozen_residual_grid_component_mass_kg"], float)
            event_cv_mass = np.asarray(z["event_CV_component_mass_kg"], float)
            e0_cv = np.asarray(z["E0_pair_cv_id"], np.int64)
            e0_cell = np.asarray(z["E0_pair_flat_cell"], np.int64)
            e2_cv = np.asarray(z["E2_pair_cv_id"], np.int64)
            e2_cell = np.asarray(z["E2_pair_flat_cell"], np.int64)
            is_e0 = np.asarray(z["E2_pair_is_E0"], bool)
            is_e1 = np.asarray(z["E2_pair_is_E1"], bool)
            target0 = np.asarray(z["E0_parent_continuity_target_kg"], float)
            qtarget0 = np.asarray(z["E0_raw_event_EOS_target_kg"], float)
            parent_pressure = np.asarray(z["parent_pressure_psi"], float)
            grid_pv = np.asarray(z["grid_pore_volume_m3"], float)
            p_ref = float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))

        a2d = drive / A2E_REL
        verify_manifest(a2d, A2E_MANIFEST)
        with np.load(a2d / A2E_EPOCH, allow_pickle=False) as z:
            epoch = {k: np.asarray(z[k]).copy() for k in z.files}
        grid_nw = np.asarray(epoch["nw"], float)
        grid_no = np.asarray(epoch["no"], float)
        grid_krw = np.asarray(epoch["krw_max"], float)
        grid_kro = np.asarray(epoch["kro_max"], float)

        gate("state_shapes_exact", event_grid0.shape == GRID and residual_grid.shape == GRID and event_cv_mass.shape == (NSL, NCV) and e2_cv.shape == (EXPECTED_E2,))

        e0_idx = np.flatnonzero(is_e0).astype(np.int64)
        gate("E0_count_exact", e0_idx.size == EXPECTED_E0, int(e0_idx.size))
        support = {
            "e2_cv": e2_cv,
            "e2_cell": e2_cell,
            "is_e0": is_e0,
            "is_e1": is_e1,
            "is_h2_shell": (~is_e0) & (~is_e1),
            "is_any_extension": (~is_e0),
        }
        demand = event_cv_mass.reshape(-1).astype(float)
        residual = residual_grid.reshape(-1).astype(float)
        target_by_edge = np.zeros(EXPECTED_E2)
        qtarget_by_edge = np.zeros(EXPECTED_E2)
        target_by_edge[e0_idx] = target0
        qtarget_by_edge[e0_idx] = qtarget0

        prep = o2.preprocess_active_graph(
            e2_cv=e2_cv, e2_cell=e2_cell, demand=demand,
            available_raw=np.ones(NCELL)
        )
        gate("full_positive_demand_frozen_E2_active_edges_exact", prep["active_edge_count"] == EXPECTED_ACTIVE, prep["active_edge_count"])
        gate("single_connected_component_exact", prep["component_count"] == 1, prep["component_count"])

        permeability_md = np.loadtxt(root / PERM, skiprows=1, dtype=float).reshape(GRID, order="C")
        kx, ky, kz = sg2.build_directional_permeability(permeability_md)
        kfx, kfy, kfz = sg2.build_face_permeabilities(kx, ky, kz)
        tx_ref, ty_ref, tz_ref = sg3.construct_si_transmissibilities(kfx, kfy, kfz)

        def pressure_step(sat):
            mob = a2e.spatial_mobility(sat, grid_nw, grid_no, grid_krw, grid_kro)
            tx, ty, tz, _ = r3r2r1.build_updated_transmissibilities(sg3, tx_ref, ty_ref, tz_ref, mob["lambda_total"])
            A, b, _ = r3r2r1.assemble_updated_pressure_system(sg3, permeability_md, tx, ty, tz, mob["lambda_total"])
            _ppa, p, res = r3r2r1.solve_updated_pressure(sg3, A, b)
            return np.asarray(p, float), float(res)

        cv_tol = max(1.0e-6, 1.0e-10 * max(float(np.max(np.abs(demand))), 1.0))

        # Iteration 1 checkpoint/restart.
        stage = "iteration1_checkpoint_or_reconstruction"
        cp1_expected = {CP1_STATE, CP1_META}
        if checkpoint_valid(checkpoints, CP1_MANIFEST, cp1_expected):
            cp1_meta = load_json(checkpoints / CP1_META)
            with np.load(checkpoints / CP1_STATE, allow_pickle=False) as z:
                p1 = np.asarray(z["P1_pressure_psi"], float)
                cap1 = np.asarray(z["P1_cell_capacity_kg"], float)
                avail1 = np.asarray(z["P1_available_mapped_capacity_kg"], float).reshape(-1)
                x1 = np.asarray(z["iteration1_E2_assignment_mass_kg"], float)
                mapped1 = np.asarray(z["iteration1_event_mapped_grid_mass_kg"], float)
                m1 = np.asarray(z["iteration1_event_grid_mass_kg"], float)
                s1 = np.asarray(z["iteration1_saturation"], float)
            gate("iteration1_checkpoint_status_exact", cp1_meta.get("milestone") == MILESTONE and cp1_meta.get("checkpoint_kind") == "CERTIFIED_NONLINEAR_ITERATION_STATE" and int(cp1_meta.get("iteration", -1)) == 1 and cp1_meta.get("scientific_state_certified") is True)
            gate("iteration1_checkpoint_shapes_exact", p1.shape == GRID and cap1.shape == GRID and s1.shape == GRID and mapped1.shape == GRID and m1.shape == GRID and x1.shape == (EXPECTED_E2,) and avail1.shape == (NCELL,))
            checkpoint_iteration1_reused = True
            print("[PASS] durable iteration-1 checkpoint validated and reused; five-stage reconstruction skipped")
        else:
            sg0 = a2e.invert_local_mass(r2, event_grid0, parent_pressure, p_ref, grid_pv)
            s0 = BACKGROUND + np.asarray(sg0, float)
            p1, p1res = pressure_step(s0)
            gate("P1_pressure_linear_residual", p1res < 1.0e-8, p1res)
            cap1 = np.asarray(a2e.local_mass(r2, np.full(GRID, INJECTED), p1, p_ref, grid_pv), float)
            avail1_raw = cap1.reshape(-1) - residual
            gate("P1_residual_feasible", float(np.min(avail1_raw)) >= -1.0e-8, float(np.min(avail1_raw)))
            avail1 = np.maximum(avail1_raw, 0.0)
            grid_tol1 = max(1.0e-6, 1.0e-10 * max(float(np.max(np.abs(cap1))), 1.0))

            parent_cap = np.asarray(a2e.local_mass(r2, np.full(GRID, INJECTED), parent_pressure, p_ref, grid_pv), float)
            initial_available = np.maximum(parent_cap.reshape(-1) - residual, 0.0)
            for cid in range(prep["component_count"]):
                a = int(prep["component_starts"][cid]); b = int(prep["component_starts"][cid + 1])
                edge_idx = prep["sorted_edge_idx"][a:b]
                comp = o2.make_component(component_id=cid, edge_idx=edge_idx, support=support, demand=demand, available_safe=initial_available, target_by_edge=target_by_edge, qtarget_by_edge=qtarget_by_edge)
                md = o2.build_component_model(comp, highspy)
                solvers.append(o3r6.PersistentComponentSolver(component_id=cid, comp=comp, model_data=md, highspy=highspy, o2=o2, output_flag=verbose_solver))
            gate("persistent_model_built", len(solvers) == 1, len(solvers))

            x1 = np.zeros(EXPECTED_E2)
            obj = {k: 0.0 for k in obj_keys}
            for s in solvers:
                rr = s.solve_iteration(nonlinear_iteration=1, available_global=avail1, cv_tol=cv_tol, grid_tol=grid_tol1)
                x1[rr["edge_idx"]] = rr["x"]
                rec_rows.extend(rr["telemetry"])
                for k, v in rr["objectives"].items():
                    obj[k] += float(v)
            for k in obj:
                gate("iteration1_" + k + "_reproduced", abs(obj[k] - original_obj[k]) <= max(1.0e-5, 1.0e-10 * max(abs(original_obj[k]), 1.0)), {"reconstructed": obj[k], "original": original_obj[k]})

            mapped1 = np.bincount(e2_cell, weights=x1, minlength=NCELL).astype(float).reshape(GRID)
            cv1 = np.bincount(e2_cv, weights=x1, minlength=NCVTOTAL).astype(float)
            m1 = residual_grid + mapped1
            cv1_linf = max_abs(cv1 - demand)
            cap1_excess = float(np.max(m1 - cap1))
            gate("iteration1_checkpoint_CV_mass_exact", cv1_linf <= cv_tol, cv1_linf)
            gate("iteration1_checkpoint_capacity_exact", cap1_excess <= grid_tol1, cap1_excess)

            sg1 = a2e.invert_local_mass(r2, m1, p1, p_ref, grid_pv)
            s1 = BACKGROUND + np.asarray(sg1, float)
            gate("iteration1_saturation_bounds", float(np.min(s1)) >= BACKGROUND - 1.0e-10 and float(np.max(s1)) <= INJECTED + 1.0e-10, [float(np.min(s1)), float(np.max(s1))])

            reconstructed1 = np.asarray(a2e.local_mass(r2, s1, p1, p_ref, grid_pv), float)
            eos1_error = max_abs(reconstructed1 - m1)
            mass1_tol = max(1.0e-8, 1.0e-10 * max(float(np.max(np.abs(m1))), 1.0))
            gate("iteration1_EOS_mass_closure", eos1_error <= mass1_tol, {"error_kg": eos1_error, "tol_kg": mass1_tol})

            cp1_state = {
                "event_day": np.asarray(EVENT_DAY),
                "iteration": np.asarray(1, dtype=np.int64),
                "P1_pressure_psi": p1,
                "P1_cell_capacity_kg": cap1,
                "P1_available_mapped_capacity_kg": avail1.reshape(GRID),
                "iteration1_E2_assignment_mass_kg": x1,
                "iteration1_event_mapped_grid_mass_kg": mapped1,
                "iteration1_event_grid_mass_kg": m1,
                "iteration1_saturation": s1,
            }
            cp1_meta = {
                "milestone": MILESTONE,
                "checkpoint_kind": "CERTIFIED_NONLINEAR_ITERATION_STATE",
                "iteration": 1,
                "event_day": EVENT_DAY,
                "scientific_state_certified": True,
                "restart_authority": "Reusable only after SHA/manifest verification and scientific recertification; no physical-time advance.",
                "O3R6_iteration1_objectives": original_obj,
                "CV_mass_Linf_kg": cv1_linf,
                "maximum_cell_capacity_excess_kg": cap1_excess,
                "EOS_cellwise_mass_error_kg": eos1_error,
                "physical_time_advanced": False,
            }
            publish_checkpoint(checkpoints, CP1_STATE, deterministic_npz_bytes(cp1_state), CP1_META, json_bytes(cp1_meta), CP1_MANIFEST)
            gate("iteration1_durable_checkpoint_published_before_P2", checkpoint_valid(checkpoints, CP1_MANIFEST, cp1_expected), str(checkpoints / CP1_STATE))
            print("[CHECKPOINT] certified iteration-1 state durably published before P2 work")
            sys.stdout.flush()

        mapped1_flat = np.asarray(mapped1, float).reshape(-1)
        cv1 = np.bincount(e2_cv, weights=x1, minlength=NCVTOTAL).astype(float)
        m1_from_x = (residual + mapped1_flat).reshape(GRID)
        gate("iteration1_restart_CV_mass_certified", max_abs(cv1 - demand) <= cv_tol, max_abs(cv1 - demand))
        gate("iteration1_restart_grid_mass_matches_assignment", max_abs(m1_from_x - m1) <= 1.0e-8, max_abs(m1_from_x - m1))
        gate("iteration1_restart_capacity_certified", float(np.max(m1 - cap1)) <= 1.0e-6, float(np.max(m1 - cap1)))
        reconstructed1 = np.asarray(a2e.local_mass(r2, s1, p1, p_ref, grid_pv), float)
        gate("iteration1_restart_EOS_mass_certified", max_abs(reconstructed1 - m1) <= max(1.0e-8, 1.0e-10 * max(float(np.max(np.abs(m1))), 1.0)), max_abs(reconstructed1 - m1))

        # P2 checkpoint/restart.
        stage = "P2_checkpoint_or_reproduction"
        cp2_expected = {CP2_STATE, CP2_META}
        if checkpoint_valid(checkpoints, CP2_MANIFEST, cp2_expected):
            cp2_meta = load_json(checkpoints / CP2_META)
            with np.load(checkpoints / CP2_STATE, allow_pickle=False) as z:
                p2 = np.asarray(z["P2_pressure_psi"], float)
                cap2 = np.asarray(z["P2_cell_capacity_kg"], float)
                avail2 = np.asarray(z["P2_available_mapped_capacity_kg"], float).reshape(-1)
                p2res = float(np.asarray(z["P2_pressure_linear_residual"]).reshape(()))
            gate("P2_checkpoint_status_exact", cp2_meta.get("milestone") == MILESTONE and cp2_meta.get("checkpoint_kind") == "DIAGNOSTIC_PRESSURE_CAPACITY_STATE" and int(cp2_meta.get("source_iteration", -1)) == 1 and int(cp2_meta.get("target_pressure_iteration", -1)) == 2)
            checkpoint_p2_reused = True
            print("[PASS] durable P2 diagnostic checkpoint validated and reused")
        else:
            p2, p2res = pressure_step(s1)
            cap2 = np.asarray(a2e.local_mass(r2, np.full(GRID, INJECTED), p2, p_ref, grid_pv), float)
            avail2_raw = cap2.reshape(-1) - residual
            cap_tol2 = max(1.0e-8, 1.0e-12 * max(float(np.max(np.abs(cap2))), 1.0))
            gate("P2_residual_sidecar_feasible", float(np.min(avail2_raw)) >= -cap_tol2, {"minimum_available": float(np.min(avail2_raw)), "tol": cap_tol2})
            avail2 = np.maximum(avail2_raw, 0.0)
            cp2_state = {
                "event_day": np.asarray(EVENT_DAY),
                "P2_pressure_psi": p2,
                "P2_cell_capacity_kg": cap2,
                "P2_available_mapped_capacity_kg": avail2.reshape(GRID),
                "P2_pressure_linear_residual": np.asarray(p2res),
            }
            cp2_meta = {
                "milestone": MILESTONE,
                "checkpoint_kind": "DIAGNOSTIC_PRESSURE_CAPACITY_STATE",
                "event_day": EVENT_DAY,
                "source_iteration": 1,
                "target_pressure_iteration": 2,
                "pressure_linear_residual": p2res,
                "scientific_state_certified": False,
                "diagnostic_state_only": True,
                "physical_time_advanced": False,
            }
            publish_checkpoint(checkpoints, CP2_STATE, deterministic_npz_bytes(cp2_state), CP2_META, json_bytes(cp2_meta), CP2_MANIFEST)
            gate("P2_durable_checkpoint_published_before_min_unserved_LP", checkpoint_valid(checkpoints, CP2_MANIFEST, cp2_expected), str(checkpoints / CP2_STATE))
            print("[CHECKPOINT] P2 diagnostic state durably published before minimum-unserved LP")
            sys.stdout.flush()

        expected_p2res = float(fr["gates"]["iteration_002_pressure_linear_residual"]["detail"])
        gate("P2_pressure_linear_residual_reproduced", abs(p2res - expected_p2res) <= 1.0e-12, {"reconstructed": p2res, "original": expected_p2res})
        gate("P2_pressure_shape_exact", p2.shape == GRID, p2.shape)
        gate("P2_capacity_shape_exact", cap2.shape == GRID, cap2.shape)
        gate("P2_available_shape_exact", avail2.shape == (NCELL,), avail2.shape)

        stage = "P2_exact_minimum_unserved_audit"
        lp, active, cv_e, cell_e, nedge, nnz = o3r4.build_feasibility_lp(highspy, coo_matrix, e2_cv, e2_cell, demand, avail2)
        gate("P2_min_unserved_uses_full_frozen_E2_positive_demand_graph", nedge == EXPECTED_ACTIVE, nedge)
        print("[START] P2 minimum-unserved feasibility solve")
        sys.stdout.flush()

        x, u, tel = o3r4.run_highs_feasibility(highspy, lp, nedge)
        del lp
        gc.collect()

        assigned = np.bincount(cv_e, weights=x, minlength=NCVTOTAL).astype(float)
        mapped = np.bincount(cell_e, weights=x, minlength=NCELL).astype(float)
        cv_linf = float(np.max(np.abs(assigned + u - demand)))
        cap_excess = float(np.max(mapped - avail2))
        unserved = float(np.sum(u))
        ids = np.flatnonzero(u > NUM_ZERO)
        exact = unserved <= NUM_ZERO

        gate("P2_min_unserved_model_CV_equalities", cv_linf <= 1.0e-6, cv_linf)
        gate("P2_min_unserved_model_cell_capacities", cap_excess <= 1.0e-6, cap_excess)

        rows = []
        edge_count = np.bincount(e2_cv, minlength=NCVTOTAL)
        for c in ids:
            rows.append({
                "cv_id": int(c),
                "streamline": int(c // NCV),
                "control_volume": int(c % NCV),
                "demand_kg": float(demand[c]),
                "minimum_unserved_kg": float(u[c]),
                "frozen_E2_candidate_edge_count": int(edge_count[c]),
            })

        classification = (
            "O3R6_STAGE1_INFEASIBILITY_NOT_RECERTIFIED_P2_EXACT_FEASIBLE_SOLVER_STATE_OR_NUMERICAL_AUDIT_REQUIRED"
            if exact else
            "O3R6_STAGE1_INFEASIBILITY_EXACTLY_RECERTIFIED_P2_FROZEN_E2_INFEASIBLE"
        )
        next_milestone = (
            "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R6-R2 — persistent-model Stage-1 infeasibility technical audit/design"
            if exact else
            "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R6-R2 — coupled-map feasible-region boundary / prospective stabilization design review"
        )

        checkpoint_policy = {
            "policy_id": "PAD_STREAM_DURABLE_CHECKPOINT_POLICY_V1",
            "effective_from_milestone": MILESTONE,
            "certified_nonlinear_iteration_rule": "After every expensive nonlinear iteration passes pressure, assignment, capacity, EOS, and mass certification, persist an immutable scientific-state checkpoint before starting the next nonlinear iteration.",
            "restart_rule": "A valid checkpoint may be reused only after manifest/SHA verification and state recertification against immutable upstream authorities.",
            "diagnostic_pressure_rule": "When a later diagnostic depends on an expensive certified state, persist the derived pressure/capacity diagnostic state before starting the expensive audit.",
            "partial_solver_stage_rule": "Future runners may persist HiGHS basis/solver-stage artifacts for computational resume, but such artifacts must be labeled COMPUTATIONAL_RESUME_ONLY and must never be treated as certified physical states.",
            "physical_time_rule": "Checkpoint creation and restart do not advance physical time and do not create new scientific execution authority.",
        }

        summary = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "event_day": EVENT_DAY,
            "O3R6_scientific_fail_bound": True,
            "O3R6R1_original_commit_preserved": PARENT_O3R6R1_COMMIT,
            "checkpoint_restart_correction_only": True,
            "scientific_audit_semantics_changed": False,
            "iteration1_checkpoint_reused": checkpoint_iteration1_reused,
            "P2_checkpoint_reused": checkpoint_p2_reused,
            "iteration1_exactly_reconstructed_or_reused_and_recertified": True,
            "iteration2_pressure_reproduced_or_reused_and_recertified": True,
            "iteration2_frozen_E2_exact_feasible": bool(exact),
            "iteration2_minimum_unserved_mass_kg": unserved,
            "iteration2_unserved_CV_count_above_1e-6_kg": int(ids.size),
            "CV_equality_Linf_kg": cv_linf,
            "maximum_cell_capacity_excess_kg": cap_excess,
            "classification": classification,
            "solver_telemetry": tel,
            "coupled_continuation_executed": False,
            "damping_used": False,
            "support_domain_changed": False,
            "physical_time_advanced": False,
        }
        decision = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "classification": classification,
            "next_milestone": next_milestone,
            "O3R6R2_design_or_audit_authorized": True,
            "O3R6R2_execution_authorized": False,
            "checkpoint_policy_frozen_for_future_expensive_iterations": True,
            "damping_execution_authorized": False,
            "support_expansion_authorized": False,
            "O3R7_authorized": False,
            "R3R3R4_authorized": False,
            "F5_dataset_generation_authorized": False,
            "training_authorized": False,
            "automatic_rerun_authorized": False,
        }
        audit = {
            **summary,
            "P1_pressure_minmax_psi": [float(np.min(p1)), float(np.max(p1))],
            "P2_pressure_minmax_psi": [float(np.min(p2)), float(np.max(p2))],
            "P2_pressure_change_from_P1_relative_L2": relative_l2(p2, p1),
            "P2_total_available_mapped_capacity_kg": fsum(avail2),
            "total_CV_demand_kg": fsum(demand),
            "gates": gates,
        }
        final_state = {
            "P1_pressure_psi": p1,
            "iteration1_event_grid_mass_kg": m1,
            "iteration1_saturation": s1,
            "iteration1_E2_assignment_mass_kg": x1,
            "P2_pressure_psi": p2,
            "P2_cell_capacity_kg": cap2,
            "P2_available_mapped_capacity_kg": avail2.reshape(GRID),
            "P2_min_unserved_by_CV_kg": u,
        }
        files = {
            "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R1R1_Summary.json": json_bytes(summary),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R1R1_Exact_Feasibility_Audit.json": json_bytes(audit),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R1R1_Iteration1_Reconstruction_Assignment_Telemetry.csv": csv_bytes(rec_rows),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R1R1_P2_Unserved_CV_Diagnostics.csv": csv_bytes(rows),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R1R1_Diagnostic_State.npz": deterministic_npz_bytes(final_state),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R1R1_Checkpoint_Restart_Policy.json": json_bytes(checkpoint_policy),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R1R1_Decision_Contract.json": json_bytes(decision),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R1R1_Final_Gate_Matrix.csv": csv_bytes([{"gate": k, **v} for k, v in gates.items()]),
        }
        immutable_publish(out, files)

        manifest = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R1R1_Artifact_Manifest.csv"
        mr = []
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name != manifest:
                mr.append({"file": p.name, "sha256": sha256_file(p), "bytes": p.stat().st_size})
        immutable_publish(out, {manifest: csv_bytes(mr)})

        print()
        print("=" * 208)
        print(MILESTONE + ": AUDIT PASS")
        print("=" * 208)
        print("Iteration-1 checkpoint reused       :", checkpoint_iteration1_reused)
        print("P2 checkpoint reused                :", checkpoint_p2_reused)
        print("P2 exact frozen-E2 feasible         :", exact)
        print("P2 minimum unserved mass kg         :", unserved)
        print("P2 unserved CV count >1e-6 kg       :", int(ids.size))
        print("Classification                       :", classification)
        print("Checkpoint policy                    : FROZEN")
        print("Coupled continuation                 : NOT EXECUTED")
        print("Damping/support expansion            : NOT AUTHORIZED")
        print("O3-R7 / R3-R3-R4                    : NOT AUTHORIZED")
        print("=" * 208)
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": MILESTONE,
            "status": STATUS_BLOCK,
            "failed_stage": stage,
            "exception": repr(exc),
            "gates": gates,
            "iteration1_checkpoint_reused": checkpoint_iteration1_reused,
            "P2_checkpoint_reused": checkpoint_p2_reused,
            "coupled_continuation_executed": False,
            "physical_time_advanced": False,
            "automatic_rerun_authorized": False,
            "O3R7_authorized": False,
            "R3R3R4_authorized": False,
        }
        p = blocked / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R1R1_Blocked_Report.json"
        if not p.exists():
            p.write_bytes(json_bytes(report))
        print()
        print(MILESTONE + ": TECHNICAL / AUTHORITY BLOCK")
        print("Stage:", stage)
        print("Exception:", repr(exc))
        return 2
    finally:
        for s in solvers:
            try:
                s.close()
            except Exception:
                pass
        gc.collect()


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--project-root", type=Path, default=Path("."))
    p.add_argument("--drive-root", type=Path, default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    p.add_argument("--verbose-solver", action="store_true")
    p.add_argument("--self-test", action="store_true")
    return p.parse_args()


if __name__ == "__main__":
    a = parse_args()
    if a.self_test:
        self_test()
        raise SystemExit(0)
    raise SystemExit(main(a.project_root, a.drive_root, a.verbose_solver))
