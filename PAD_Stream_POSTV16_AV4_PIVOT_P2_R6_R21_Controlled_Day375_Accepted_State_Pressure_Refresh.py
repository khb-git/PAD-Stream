#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np

M = "POSTV16-AV4-PIVOT-P2-R6-R21"
NAME = "Controlled Day375 Accepted-State Pressure Refresh"

PASS = "AV4PIVOTP2R6R21_DAY375_ACCEPTED_STATE_PRESSURE_REFRESH_PASS_NO_TIME_ADVANCE"
SCI_FAIL = "AV4PIVOTP2R6R21_DAY375_ACCEPTED_STATE_PRESSURE_REFRESH_SCIENTIFIC_FAIL"
BLOCK = "AV4PIVOTP2R6R21_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "5080e81d363db262495209fbfda6d3c6290445ed"

R20_RUNNER = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R20_Day375_Global_Closure_and_Acceptance_Audit.py"
R20_BLOB = "3f872ed6a5cf2e8b4cb15f0c6f2fdeea99565d53"

A2E_RUNNER = "PAD_Stream_POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution.py"
A2E_BLOB = "79a8969233b72b4543edd382a0c3d1028c6dca09"

R2 = "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"
SG2 = "PAD_Stream_V15SG2_Anisotropic_Transmissibility.py"
SG2_BLOB = "7242012d3e758472abc3ee7f543831b92d2cf419"
SG3 = "PAD_Stream_V15SG3_FiveSpot_Pressure_Solve.py"
SG3_BLOB = "66a379cd97ee9120f69e7e7e949171541e4918c3"
R3 = "PAD_Stream_V16E41R3R2R1_Local_Conservation_Sign_Convention_Repair.py"
R3_BLOB = "740c6da03e73906646bf0153633187e749449f31"
PERM = "SGSIM_50x50x15_PERM_MD.csv"
PERM_BLOB = "317dd47d458bc6f880c2e3dc4ec1f69eeb0dd314"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

R20 = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R20_Day375_Globally_Reconciled_"
    "Provisional_State_Closure_and_Acceptance_Audit"
)
R19 = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R19_Controlled_Day375_Remaining_NonExecuted_R7_"
    "Group_Coupled_Global_CVConservative_Reconciliation_Execution"
)
A2E = BASE / "POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution"

BASE_AV3 = Path("post_v16") / RID / "POSTV16_AV3_Corey_Relperm_Heterogeneity"
A6E = BASE_AV3 / "POSTV16_AV3_A6_E_Frozen_Checkpoint_LocalPV_R7D_Integration_Execution"

R19_STATE = "POSTV16_AV4_PIVOT_P2_R6_R19_Provisional_Globally_Reconciled_Day375_State.npz"
R19_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R19_Artifact_Manifest.csv"

R20_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R20_Summary.json"
R20_DECISION = "POSTV16_AV4_PIVOT_P2_R6_R20_Decision_Contract.json"
R20_ACCEPTANCE = "POSTV16_AV4_PIVOT_P2_R6_R20_Day375_State_Acceptance_Contract.json"
R20_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R20_Artifact_Manifest.csv"

A2E_EPOCH = "POSTV16_AV4_A2_E_Refreshed_Flow_Epoch.npz"
A2E_MANIFEST = "POSTV16_AV4_A2_E_Artifact_Manifest.csv"
A6E_STATE = "POSTV16_AV3_A6_E_AV3CR0003_Integrated_State.npz"
A6E_STATE_SHA = "f9e3a7bd8c6dcc43d522e0cb99a0cede2bd212fd570085b4faf82dc71af8f803"

OUT = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R21_Controlled_Day375_Accepted_State_Pressure_Refresh"
)
FAIL = BASE / "POSTV16_AV4_PIVOT_P2_R6_R21_SCIENTIFIC_FAIL"
BLK = BASE / "POSTV16_AV4_PIVOT_P2_R6_R21_BLOCKED"

GRID = (15, 50, 50)
NCELL = 37500
DAY = 375.0

CELL_MASS_ABS_TOL = 1e-7
GLOBAL_MASS_REL_TOL = 1e-10
PRESSURE_PARENT_BIND_TOL = 1e-12


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


def manifest(directory: Path, filename: str) -> None:
    for row in csvr(directory / filename):
        p = directory / row["file"]
        if not p.is_file():
            raise GateError(f"manifest_missing:{p.name}")
        if sha(p) != row["sha256"]:
            raise GateError(f"manifest_sha:{p.name}")
        if p.stat().st_size != int(row["bytes"]):
            raise GateError(f"manifest_bytes:{p.name}")


def mod(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError(f"cannot_load:{path}")
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def max_abs(a: np.ndarray) -> float:
    return float(np.max(np.abs(np.asarray(a, dtype=float))))


def relative_l2(new: np.ndarray, old: np.ndarray) -> float:
    a = np.asarray(new, dtype=float)
    b = np.asarray(old, dtype=float)
    return float(np.linalg.norm((a - b).ravel()) / max(float(np.linalg.norm(b.ravel())), 1e-30))


def selftest() -> None:
    assert GRID == (15, 50, 50)
    assert DAY == 375.0
    assert GLOBAL_MASS_REL_TOL == 1e-10
    print("POSTV16 AV4 PIVOT P2-R6-R21 structural self-test: PASS")


def main(root: Path, drive: Path) -> int:
    root = root.resolve()
    drive = drive.resolve()
    out = drive / OUT
    fail = drive / FAIL
    block = drive / BLK
    stage = "preflight"
    gates: list[dict[str, Any]] = []
    scientific_started = False

    def gate(name: str, cond: Any, detail: Any = None) -> None:
        ok = bool(cond)
        gates.append({
            "stage": stage,
            "gate": name,
            "pass": ok,
            "detail": "" if detail is None else repr(detail),
            "scientific": False,
        })
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + ("" if detail is None else f" -- {detail}"))
        if not ok:
            raise GateError(name)

    def sci_gate(name: str, cond: Any, detail: Any = None) -> None:
        ok = bool(cond)
        gates.append({
            "stage": stage,
            "gate": name,
            "pass": ok,
            "detail": "" if detail is None else repr(detail),
            "scientific": True,
        })
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + ("" if detail is None else f" -- {detail}"))
        if not ok:
            raise ScientificFail(name, detail)

    try:
        summary_path = out / "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R21_Summary.json"
        block_path = block / "POSTV16_AV4_PIVOT_P2_R6_R21_Blocked_Report.json"
        fail_path = fail / "POSTV16_AV4_PIVOT_P2_R6_R21_Scientific_Fail_Report.json"

        if summary_path.is_file():
            print("[PASS] formal R6-R21 PASS already exists; immutable outcome preserved.")
            return 0
        gate("no_preexisting_R6R21_BLOCK", not block_path.exists())
        gate("no_preexisting_R6R21_SCIENTIFIC_FAIL", not fail_path.exists())

        stage = "repository_authority"
        gate("branch_exact", gt(root, "branch", "--show-current") == BRANCH)
        gate("parent_is_R6R20", gt(root, "rev-parse", "HEAD^") == PARENT)
        gate("repository_clean", gt(root, "status", "--porcelain") == "")
        for filename, blob, label in [
            (R20_RUNNER, R20_BLOB, "R6R20"),
            (A2E_RUNNER, A2E_BLOB, "A2E"),
            (R2, R2_BLOB, "R2"),
            (SG2, SG2_BLOB, "SG2"),
            (SG3, SG3_BLOB, "SG3"),
            (R3, R3_BLOB, "R3R2R1"),
            (PERM, PERM_BLOB, "PERM"),
        ]:
            gate(
                f"{label}_blob_exact",
                gt(root, "hash-object", str(root / filename)) == blob,
            )

        stage = "R6R20_acceptance_authority"
        r20 = drive / R20
        manifest(r20, R20_MANIFEST)
        s20 = js(r20 / R20_SUMMARY)
        d20 = js(r20 / R20_DECISION)
        a20_path = r20 / R20_ACCEPTANCE
        a20 = js(a20_path)

        gate("R6R20_status_exact", s20.get("status") == "AV4PIVOTP2R6R20_DAY375_GLOBAL_CLOSURE_AND_ACCEPTANCE_AUDIT_PASS_ACCEPTED_STATE")
        gate("accepted_Day375_state_true", a20.get("accepted_Day375_state") is True)
        accepted_sha = str(a20["accepted_Day375_state_sha256"])
        gate("accepted_state_SHA_matches_summary", accepted_sha == s20["accepted_Day375_state_sha256"])
        gate("R6R21_authorized", d20.get("P2_R6_R21_authorized") is True)
        gate("R6R21_pressure_refresh_authorized", d20.get("P2_R6_R21_pressure_refresh_execution_authorized") is True)
        gate("Darcy_Pollock_TOF_still_locked", d20.get("Darcy_Pollock_TOF_regeneration_authorized") is False)
        gate("time_advance_still_locked", d20.get("time_advance_authorized") is False)
        acceptance_sha = sha(a20_path)
        gate("acceptance_contract_SHA_matches_summary", acceptance_sha == s20["acceptance_contract_sha256"], acceptance_sha)

        stage = "accepted_state_load"
        r19 = drive / R19
        manifest(r19, R19_MANIFEST)
        state_path = r19 / R19_STATE
        gate("accepted_state_file_SHA_exact", sha(state_path) == accepted_sha, sha(state_path))

        with np.load(state_path, allow_pickle=False) as z:
            accepted_mass = np.asarray(z["provisional_grid_component_mass_kg"], dtype=float).reshape(GRID)
            inherited_pressure = np.asarray(z["parent_pressure_psi"], dtype=float)
            state_day = float(np.asarray(z["state_day"]).reshape(()))

        gate("accepted_state_day_375", abs(state_day - DAY) <= 1e-12, state_day)
        gate("accepted_mass_shape_finite", accepted_mass.shape == GRID and np.isfinite(accepted_mass).all())
        gate("accepted_mass_nonnegative_with_tolerance", float(np.min(accepted_mass)) >= -CELL_MASS_ABS_TOL, float(np.min(accepted_mass)))
        accepted_mass = np.maximum(accepted_mass, 0.0)
        gate("inherited_pressure_shape_finite", inherited_pressure.shape == GRID and np.isfinite(inherited_pressure).all())

        stage = "frozen_property_authority"
        a2e = mod(root / A2E_RUNNER, "r6r21_a2e")
        r2 = mod(root / R2, "r6r21_r2")
        sg2 = mod(root / SG2, "r6r21_sg2")
        sg3 = mod(root / SG3, "r6r21_sg3")
        r3 = mod(root / R3, "r6r21_r3")

        control_path = drive / A6E / A6E_STATE
        gate("A6E_control_state_present", control_path.is_file(), str(control_path))
        gate("A6E_control_state_SHA_exact", sha(control_path) == A6E_STATE_SHA, sha(control_path))

        with np.load(control_path, allow_pickle=False) as z:
            phi = np.asarray(z["paired_porosity"], dtype=float)
            nw = np.asarray(z["nw"], dtype=float)
            no = np.asarray(z["no"], dtype=float)
            krw_max = np.asarray(z["krw_max"], dtype=float)
            kro_max = np.asarray(z["kro_max"], dtype=float)

        for label, arr in [
            ("phi", phi), ("nw", nw), ("no", no),
            ("krw_max", krw_max), ("kro_max", kro_max),
        ]:
            gate(f"{label}_shape_finite", arr.shape == GRID and np.isfinite(arr).all())

        pore_volume = phi * float(a2e.BULK_VOLUME_M3)
        gate("pore_volume_positive", np.all(pore_volume > 0.0))

        stage = "inherited_pressure_binding"
        a2edir = drive / A2E
        manifest(a2edir, A2E_MANIFEST)
        with np.load(a2edir / A2E_EPOCH, allow_pickle=False) as z:
            day365_pressure = np.asarray(z["refreshed_pressure_psi"], dtype=float)

        parent_pressure_delta = max_abs(inherited_pressure - day365_pressure)
        gate("accepted_state_inherited_pressure_is_frozen_Day365_epoch", parent_pressure_delta <= PRESSURE_PARENT_BIND_TOL, parent_pressure_delta)

        p_ref = float(a2e.reference_gas_pressure_pa(r2, inherited_pressure))

        try:
            parent_sg = a2e.invert_local_mass(
                r2,
                accepted_mass,
                inherited_pressure,
                p_ref,
                pore_volume,
            )
        except Exception as exc:
            raise GateError(f"accepted_state_parent_EOS_inversion:{repr(exc)}") from exc

        parent_sat = float(a2e.BACKGROUND) + np.asarray(parent_sg, dtype=float)
        parent_reconstructed = np.asarray(
            a2e.local_mass(r2, parent_sat, inherited_pressure, p_ref, pore_volume),
            dtype=float,
        )
        parent_mass_max_error = max_abs(parent_reconstructed - accepted_mass)
        parent_mass_global_rel = abs(float(parent_reconstructed.sum() - accepted_mass.sum())) / max(abs(float(accepted_mass.sum())), 1.0)
        gate("accepted_parent_mass_reconstruction_cellwise", parent_mass_max_error <= CELL_MASS_ABS_TOL, parent_mass_max_error)
        gate("accepted_parent_mass_reconstruction_global", parent_mass_global_rel <= GLOBAL_MASS_REL_TOL, parent_mass_global_rel)

        permeability = np.loadtxt(root / PERM, skiprows=1, dtype=float).reshape(GRID, order="C")
        gate("permeability_shape_finite_positive", permeability.shape == GRID and np.isfinite(permeability).all() and np.all(permeability > 0.0))

        scientific_started = True
        stage = "same_time_pressure_saturation_fixed_point"

        try:
            refresh = a2e.fixed_point_refresh(
                r2=r2,
                r3r2r1=r3,
                sg2=sg2,
                sg3=sg3,
                permeability_md=permeability,
                parent_mass=accepted_mass,
                parent_saturation=parent_sat,
                parent_pressure_psi=inherited_pressure,
                p_ref_gas_pa=p_ref,
                pore_volume_m3=pore_volume,
                nw=nw,
                no=no,
                krw_max=krw_max,
                kro_max=kro_max,
                sci_gate=sci_gate,
            )
        except a2e.ScientificFail as exc:
            raise ScientificFail(str(exc.gate), exc.detail) from exc

        refreshed_pressure = np.asarray(refresh["pressure_psi"], dtype=float)
        reconciled_sat = np.asarray(refresh["saturation"], dtype=float)
        tx = np.asarray(refresh["tx"], dtype=float)
        ty = np.asarray(refresh["ty"], dtype=float)
        tz = np.asarray(refresh["tz"], dtype=float)
        mobility = refresh["mobility"]

        stage = "post_refresh_mass_and_state_validation"
        post_mass = np.asarray(
            a2e.local_mass(r2, reconciled_sat, refreshed_pressure, p_ref, pore_volume),
            dtype=float,
        )
        max_cell_mass_error = max_abs(post_mass - accepted_mass)
        global_mass_rel = abs(float(post_mass.sum() - accepted_mass.sum())) / max(abs(float(accepted_mass.sum())), 1.0)

        sci_gate("post_refresh_cellwise_mass_exact", max_cell_mass_error <= CELL_MASS_ABS_TOL, max_cell_mass_error)
        sci_gate("post_refresh_global_mass_exact", global_mass_rel <= GLOBAL_MASS_REL_TOL, global_mass_rel)
        sci_gate("refreshed_pressure_finite", refreshed_pressure.shape == GRID and np.isfinite(refreshed_pressure).all())
        sci_gate(
            "reconciled_saturation_bounds",
            float(np.min(reconciled_sat)) >= float(a2e.BACKGROUND) - 1e-12
            and float(np.max(reconciled_sat)) <= float(a2e.INJECTED) + 1e-12,
            (float(np.min(reconciled_sat)), float(np.max(reconciled_sat))),
        )
        sci_gate("transmissibilities_finite", np.isfinite(tx).all() and np.isfinite(ty).all() and np.isfinite(tz).all())

        pressure_rel_vs_parent = relative_l2(refreshed_pressure, inherited_pressure)
        pressure_max_abs_change = max_abs(refreshed_pressure - inherited_pressure)
        saturation_linf_vs_parent = max_abs(reconciled_sat - parent_sat)

        stage = "artifact_publication"
        out.mkdir(parents=True, exist_ok=False)

        epoch_path = out / "POSTV16_AV4_PIVOT_P2_R6_R21_Day375_Pressure_Refresh_Epoch.npz"
        np.savez_compressed(
            epoch_path,
            accepted_Day375_component_mass_kg=accepted_mass,
            inherited_pressure_psi=inherited_pressure,
            parent_saturation=parent_sat,
            reconciled_saturation=reconciled_sat,
            refreshed_pressure_psi=refreshed_pressure,
            lambda_total=np.asarray(mobility["lambda_total"], dtype=float),
            lambda_w=np.asarray(mobility["lambda_w"], dtype=float),
            lambda_o=np.asarray(mobility["lambda_o"], dtype=float),
            krw=np.asarray(mobility["krw"], dtype=float),
            kro=np.asarray(mobility["kro"], dtype=float),
            Tx_dynamic=tx,
            Ty_dynamic=ty,
            Tz_dynamic=tz,
            paired_porosity=phi,
            pore_volume_m3=pore_volume,
            nw=nw,
            no=no,
            krw_max=krw_max,
            kro_max=kro_max,
            reference_gas_pressure_pa=np.asarray(p_ref, dtype=float),
            canonical_day=np.asarray(DAY, dtype=float),
            accepted_state_sha256=np.asarray(accepted_sha),
            R6R20_acceptance_contract_sha256=np.asarray(acceptance_sha),
            physical_time_advance=np.asarray(False),
        )
        epoch_sha = sha(epoch_path)

        (out / "POSTV16_AV4_PIVOT_P2_R6_R21_Fixed_Point_Iteration_Audit.csv").write_bytes(
            csvb(refresh["rows"])
        )

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": "R6R21_DAY375_ACCEPTED_STATE_PRESSURE_REFRESH_PASS_FLOW_GEOMETRY_REGENERATION_NEXT",
            "accepted_Day375_state_sha256": accepted_sha,
            "R6R20_acceptance_contract_sha256": acceptance_sha,
            "pressure_refresh_epoch_sha256": epoch_sha,
            "canonical_day": DAY,
            "fixed_point_iterations": int(refresh["iterations"]),
            "final_pressure_fixed_point_relative_L2_consistency": float(refresh["pressure_consistency"]),
            "final_saturation_fixed_point_Linf_consistency": float(refresh["saturation_consistency"]),
            "pressure_relative_L2_vs_inherited": pressure_rel_vs_parent,
            "pressure_max_abs_change_psi": pressure_max_abs_change,
            "saturation_Linf_vs_parent": saturation_linf_vs_parent,
            "final_cellwise_mass_error_kg": max_cell_mass_error,
            "final_global_mass_relative_error": global_mass_rel,
            "refreshed_pressure_min_psi": float(np.min(refreshed_pressure)),
            "refreshed_pressure_max_psi": float(np.max(refreshed_pressure)),
            "reconciled_saturation_min": float(np.min(reconciled_sat)),
            "reconciled_saturation_max": float(np.max(reconciled_sat)),
            "pressure_refresh_executed": True,
            "Darcy_Pollock_TOF_regeneration_executed": False,
            "time_advance_executed": False,
            "P3_authorized": False,
        }

        contract = {
            "milestone": M,
            "status": PASS,
            "accepted_state_authority": {
                "accepted_Day375_state_sha256": accepted_sha,
                "R6R20_acceptance_contract_sha256": acceptance_sha,
            },
            "pressure_refresh_contract": {
                "same_time_mass_preserving_fixed_point": True,
                "physics_authority": "POSTV16_AV4_A2_E_frozen_fixed_point_refresh",
                "new_pressure_formulation_introduced": False,
                "accepted_Cartesian_mass_immutable": True,
                "spatial_Corey_properties_frozen": True,
                "permeability_frozen": True,
                "physical_time_advance": False,
                "Darcy_fluxes_not_regenerated_here": True,
                "Pollock_streamlines_not_regenerated_here": True,
                "TOF_not_regenerated_here": True,
            },
            "pressure_refresh_epoch_sha256": epoch_sha,
        }

        decision = {
            "milestone": M,
            "status": PASS,
            "classification": summary["classification"],
            "accepted_Day375_state_sha256": accepted_sha,
            "P2_R6_R22_authorized": True,
            "P2_R6_R22_name": "Controlled Day375 Accepted-State Darcy/Pollock/TOF Regeneration",
            "P2_R6_R22_flow_geometry_regeneration_authorized": True,
            "P2_R6_R22_must_bind_R6R21_pressure_epoch_SHA": True,
            "pressure_refresh_authorized": True,
            "Darcy_Pollock_TOF_regeneration_authorized": True,
            "time_advance_authorized": False,
            "P3_authorized": False,
            "P4_authorized": False,
            "P5_training_authorized": False,
        }

        (out / "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R21_Summary.json").write_bytes(jb(summary))
        (out / "POSTV16_AV4_PIVOT_P2_R6_R21_Pressure_Refresh_Contract.json").write_bytes(jb(contract))
        (out / "POSTV16_AV4_PIVOT_P2_R6_R21_Decision_Contract.json").write_bytes(jb(decision))
        (out / "POSTV16_AV4_PIVOT_P2_R6_R21_Final_Gate_Matrix.csv").write_bytes(csvb(gates))

        rows = []
        for p in sorted(out.iterdir()):
            if p.is_file():
                rows.append({"file": p.name, "sha256": sha(p), "bytes": p.stat().st_size})
        (out / "POSTV16_AV4_PIVOT_P2_R6_R21_Artifact_Manifest.csv").write_bytes(csvb(rows))

        print("=" * 190)
        print(M, "PASS")
        print("Accepted Day375 state SHA256             :", accepted_sha)
        print("Pressure refresh epoch SHA256            :", epoch_sha)
        print("Fixed-point iterations                   :", refresh["iterations"])
        print("Pressure rel L2 vs inherited             :", pressure_rel_vs_parent)
        print("Pressure max abs change psi              :", pressure_max_abs_change)
        print("Saturation Linf vs parent                :", saturation_linf_vs_parent)
        print("Final cellwise mass error kg             :", max_cell_mass_error)
        print("Final global mass relative error         :", global_mass_rel)
        print("Pressure refresh executed                : True")
        print("R6-R22 Darcy/Pollock/TOF authorized      : True")
        print("Time advance / P3                        : False / False")
        print("=" * 190)
        return 0

    except ScientificFail as exc:
        fail.mkdir(parents=True, exist_ok=True)
        p = fail / "POSTV16_AV4_PIVOT_P2_R6_R21_Scientific_Fail_Report.json"
        if not p.exists():
            p.write_bytes(jb({
                "milestone": M,
                "status": SCI_FAIL,
                "failed_stage": stage,
                "failed_gate": exc.gate,
                "detail": exc.detail,
                "accepted_Day375_state_preserved": True,
                "pressure_refresh_accepted": False,
                "automatic_adaptation_or_rerun_authorized": False,
                "Darcy_Pollock_TOF_regeneration_authorized": False,
                "time_advance_authorized": False,
                "P3_authorized": False,
                "gates_completed": gates,
            }))
        print(M, "SCIENTIFIC FAIL")
        print("Stage:", stage)
        print("Gate :", exc.gate)
        print("Detail:", exc.detail)
        return 3

    except Exception as exc:
        block.mkdir(parents=True, exist_ok=True)
        p = block / "POSTV16_AV4_PIVOT_P2_R6_R21_Blocked_Report.json"
        if not p.exists():
            p.write_bytes(jb({
                "milestone": M,
                "status": BLOCK,
                "failed_stage": stage,
                "exception": repr(exc),
                "accepted_Day375_state_preserved": True,
                "pressure_refresh_accepted": False,
                "automatic_rerun_authorized": False,
                "Darcy_Pollock_TOF_regeneration_authorized": False,
                "time_advance_authorized": False,
                "P3_authorized": False,
                "gates_completed": gates,
            }))
        print(M, "BLOCKED")
        print("Stage:", stage)
        print("Exception:", repr(exc))
        return 2


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", type=Path, default=Path("."))
    ap.add_argument("--drive-root", type=Path, default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        selftest()
        raise SystemExit(0)
    raise SystemExit(main(a.project_root, a.drive_root))
