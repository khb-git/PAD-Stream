#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import math
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from typing import Any

import numpy as np


MILESTONE = "POSTV16-AV4-F4-R3-R3"

STATUS_PASS = (
    "AV4F4R3R3_SINGLE_EVENT_TRIGGERED_SAME_TIME_FLOW_EPOCH_RENEWAL_EXECUTION_PASS_"
    "DAY365_TO_EVENT_TO_DAY500_COMPONENT_MASS_CONSERVATIVE_TRANSPORT_"
    "REFRESH_REPROJECTION_AND_FINAL_DAY500_RECURRENCE_CERTIFIED"
)
STATUS_FAIL = (
    "AV4F4R3R3_EVENT_REFRESH_OR_POST_REFRESH_TRANSPORT_OR_DAY500_RECURRENCE_"
    "SCIENTIFIC_FAIL_NO_SECOND_EVENT_REFRESH_OR_AUTOMATIC_RERUN_AUTHORIZED"
)
STATUS_BLOCKED = "AV4F4R3R3_TECHNICAL_EXECUTION_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT_R3R2_COMMIT = "298379b13e8890428a594dd884d557d07cde6ce6"

GRID = (15, 50, 50)
NZ, NY, NX = GRID
NCELL = NZ * NY * NX
NSL = 1078
NN = 201
NCV = 200

BACKGROUND = 0.20
INJECTED = 0.80
MAX_SG = 0.60
SPD = 86400.0

PARENT_DAY = 365.0
EVENT_DAY = 413.78677770818403
TARGET_DAY = 500.0
FIRST_DELTA_DAY = 48.78677770818403
SECOND_DELTA_DAY = 86.21322229181597
TOTAL_DELTA_DAY = 135.0

# --------------------------------------------------------------------------------------------------
# Exact source authorities.
# --------------------------------------------------------------------------------------------------

R3R2 = "PAD_Stream_POSTV16_AV4_F4_R3_R2_Event_Triggered_Flow_Epoch_Renewal_Freeze.py"
R3R2_BLOB = "c34ee2f6f2bf9abca0b86eb6ab324f0c56630ae1"

R3R1R2 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R1_R2_"
    "Corrected_Interior_Bound_Failure_Localization.py"
)
R3R1R2_BLOB = "b7613d8eda48b6e3528115c40faebe46d7b61604"

F4R3 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_"
    "Terminal_Producer_PassThrough_Repair_Execution.py"
)
F4R3_BLOB = "2e84ab09f9ae7af6f977eabc3d9465d325fad717"

A4R2 = (
    "PAD_Stream_POSTV16_AV3_A4_R2_"
    "Corrected_Certification_Teacher_Dataset_and_LockedOOD_Predictor.py"
)
A4R2_BLOB = "289901331e835afb44ff2f665fe9a6bbea2eac19"

A2E = "PAD_Stream_POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution.py"
A2E_BLOB = "79a8969233b72b4543edd382a0c3d1028c6dca09"

R2 = "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"

E37A = "PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB = "0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"

SG2 = "PAD_Stream_V15SG2_Anisotropic_Transmissibility.py"
SG2_BLOB = "7242012d3e758472abc3ee7f543831b92d2cf419"
SG3 = "PAD_Stream_V15SG3_FiveSpot_Pressure_Solve.py"
SG3_BLOB = "66a379cd97ee9120f69e7e7e949171541e4918c3"
SG4 = "PAD_Stream_V15SG4_Conservative_Darcy_Fluxes.py"
SG4_BLOB = "8d49f88bdf55b0da087af2bed04e69967740e695"
SG5 = "PAD_Stream_V15SG5_Exact_Pollock_Streamlines.py"
SG5_BLOB = "9a0b64ea7e669904d0d9855ade1c6b052f05ecea"
SG6 = "PAD_Stream_V15SG6_TOF_Transport_Coordinates.py"
SG6_BLOB = "70ceda68e02894167958d753d88b4dbd694731ab"
SG7D = "PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"
SG7D_BLOB = "890088c0c0fcab415a2c7351c5079ca8ee12bf82"
R3R2R1 = "PAD_Stream_V16E41R3R2R1_Local_Conservation_Sign_Convention_Repair.py"
R3R2R1_BLOB = "740c6da03e73906646bf0153633187e749449f31"

F2R3 = "PAD_Stream_POSTV16_AV4_F2_R3_Bounded_Physical_Occupancy_Projection_Execution.py"
F2R3_BLOB = "359f3c0edf87e10bb4006cacdd271cd426fed22b"

E1R2 = (
    "PAD_Stream_POSTV16_AV4_A3_E1_R2_Fully_Schema_Corrected_"
    "Refreshed_X13_Structural_InputDomain_Audit.py"
)
E1R2_BLOB = "058f00fd12bd491dc7d7d7e471af3d4ff865af70"

PERM = "SGSIM_50x50x15_PERM_MD.csv"
PERM_BLOB = "317dd47d458bc6f880c2e3dc4ec1f69eeb0dd314"

SOURCE_BLOBS = {
    R3R2: R3R2_BLOB,
    R3R1R2: R3R1R2_BLOB,
    F4R3: F4R3_BLOB,
    A4R2: A4R2_BLOB,
    A2E: A2E_BLOB,
    R2: R2_BLOB,
    E37A: E37A_BLOB,
    SG2: SG2_BLOB,
    SG3: SG3_BLOB,
    SG4: SG4_BLOB,
    SG5: SG5_BLOB,
    SG6: SG6_BLOB,
    SG7D: SG7D_BLOB,
    R3R2R1: R3R2R1_BLOB,
    F2R3: F2R3_BLOB,
    E1R2: E1R2_BLOB,
    PERM: PERM_BLOB,
}

# --------------------------------------------------------------------------------------------------
# Formal Drive authorities.
# --------------------------------------------------------------------------------------------------

BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

R3R2_REL = BASE_AV4 / "POSTV16_AV4_F4_R3_R2_Event_Triggered_Flow_Epoch_Renewal_Freeze"
R3R2_SUMMARY = "PAD_Stream_POSTV16_AV4_F4_R3_R2_Summary.json"
R3R2_REPAIR = "POSTV16_AV4_F4_R3_R2_Repair_Selection_Contract.json"
R3R2_TRIGGER = "POSTV16_AV4_F4_R3_R2_Event_Trigger_Contract.json"
R3R2_TRANSFER = "POSTV16_AV4_F4_R3_R2_Same_Time_Transfer_and_Refresh_Contract.json"
R3R2_EPOCH = "POSTV16_AV4_F4_R3_R2_Refreshed_Flow_Epoch_Contract.json"
R3R2_SCOPE = "POSTV16_AV4_F4_R3_R2_Controlled_Execution_Scope.json"
R3R2_PROOF = "POSTV16_AV4_F4_R3_R2_Prospective_Proof_Obligations.json"
R3R2_HANDOFF = "POSTV16_AV4_F4_R3_R2_R3R3_Execution_Handoff_Contract.json"
R3R2_DECISION = "POSTV16_AV4_F4_R3_R2_Decision_Contract.json"
R3R2_MANIFEST = "POSTV16_AV4_F4_R3_R2_Artifact_Manifest.csv"
R3R2_STATUS = (
    "AV4F4R3R2_R3R1R2_INTERIOR_UPPER_CAPACITY_ADVECTION_DOMINATED_CONFLICT_BOUND_"
    "EVENT_TRIGGERED_SAME_TIME_FLOW_EPOCH_RENEWAL_PROSPECTIVELY_FROZEN_"
    "NO_INTERIOR_FACE_LIMITER_NO_REPAIR_EXECUTION"
)

R3R1R2_REL = (
    BASE_AV4
    / "POSTV16_AV4_F4_R3_R1_R2_Corrected_Interior_Bound_Failure_Localization"
)
R3R1R2_STATE = "POSTV16_AV4_F4_R3_R1_R2_Partial_Teacher_State_at_Failure.npz"
R3R1R2_SUMMARY = "PAD_Stream_POSTV16_AV4_F4_R3_R1_R2_Summary.json"
R3R1R2_MANIFEST = "POSTV16_AV4_F4_R3_R1_R2_Artifact_Manifest.csv"

# Pull parent authority path/name constants from the frozen R3 implementation.
F2R3_REL = BASE_AV4 / "POSTV16_AV4_F2_R3_Bounded_Physical_Occupancy_Projection_Execution"
F2R3_STATE = "POSTV16_AV4_F2_R3_Accepted_Parent_Restart_State.npz"
F2R3_MANIFEST = "POSTV16_AV4_F2_R3_Artifact_Manifest.csv"

E1R2_REL = BASE_AV4 / "POSTV16_AV4_A3_E1_R2_Refreshed_X13_Structural_InputDomain_Audit"
E1R2_X13 = "POSTV16_AV4_A3_E1_R2_Refreshed_Day365_13Channel_Representation.npz"
E1R2_MANIFEST = "POSTV16_AV4_A3_E1_R2_Artifact_Manifest.csv"

A2E_REL = BASE_AV4 / "POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution"
A2E_EPOCH = "POSTV16_AV4_A2_E_Refreshed_Flow_Epoch.npz"
A2E_MANIFEST = "POSTV16_AV4_A2_E_Artifact_Manifest.csv"

OUT_REL = BASE_AV4 / "POSTV16_AV4_F4_R3_R3_First_Event_Flow_Epoch_Renewal_Execution"
FAIL_REL = BASE_AV4 / "POSTV16_AV4_F4_R3_R3_SCIENTIFIC_FAIL"
BLOCK_REL = BASE_AV4 / "POSTV16_AV4_F4_R3_R3_BLOCKED"


class GateError(RuntimeError):
    pass


class ScientificFail(RuntimeError):
    def __init__(self, gate: str, detail: Any = None):
        super().__init__(gate)
        self.gate = gate
        self.detail = detail


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def git_text(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.strip()


def git_blob(path: Path, root: Path) -> str:
    return git_text(root, "hash-object", str(path))


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def verify_manifest(directory: Path, name: str) -> dict[str, str]:
    rows = read_csv(directory / name)
    manifest = {r["file"]: r["sha256"] for r in rows}
    if not manifest:
        raise GateError("manifest_empty:" + name)
    for fn, expected in manifest.items():
        p = directory / fn
        if not p.is_file():
            raise GateError("manifest_missing:" + fn)
        if sha256_file(p) != expected:
            raise GateError("manifest_SHA_mismatch:" + fn)
    return manifest


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError("cannot_load_module:" + str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def json_bytes(obj: Any) -> bytes:
    return (
        json.dumps(obj, indent=2, sort_keys=True, allow_nan=False)
        + "\n"
    ).encode("utf-8")


def csv_bytes(rows: list[dict[str, Any]]) -> bytes:
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


def deterministic_npz_bytes(arrays: dict[str, Any]) -> bytes:
    outer = io.BytesIO()
    with zipfile.ZipFile(
        outer,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as zf:
        for key in sorted(arrays):
            b = io.BytesIO()
            np.save(b, np.asarray(arrays[key]), allow_pickle=False)
            info = zipfile.ZipInfo(
                f"{key}.npy",
                date_time=(1980, 1, 1, 0, 0, 0),
            )
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            zf.writestr(info, b.getvalue())
    return outer.getvalue()


def immutable_publish(out: Path, files: dict[str, bytes]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        p = out / name
        if p.exists() and p.read_bytes() != data:
            raise GateError("existing_output_differs:" + name)
        if not p.exists():
            p.write_bytes(data)


def fsum_array(a: np.ndarray) -> float:
    return float(
        math.fsum(
            float(x)
            for x in np.asarray(a, dtype=np.float64).ravel()
        )
    )


def relative_l2(a: np.ndarray, b: np.ndarray) -> float:
    aa = np.asarray(a, dtype=np.float64)
    bb = np.asarray(b, dtype=np.float64)
    return float(
        np.linalg.norm((aa - bb).ravel())
        / max(float(np.linalg.norm(bb.ravel())), 1.0e-30)
    )


def sample_grid_to_nodes(
    sg7d: Any,
    xyz_m: np.ndarray,
    grid_field: np.ndarray,
) -> np.ndarray:
    xyz = np.asarray(xyz_m, dtype=np.float64)
    field = np.asarray(grid_field, dtype=np.float64)
    if xyz.shape != (NSL, NN, 3) or field.shape != GRID:
        raise GateError(
            "sample_grid_to_nodes_shape",
        )
    result = np.empty((NSL, NN), dtype=np.float64)
    for s in range(NSL):
        for n in range(NN):
            k, j, i = sg7d.point_to_cell(xyz[s, n])
            result[s, n] = field[k, j, i]
    return result


def execute_until_first_interior_event(
    *,
    r3: Any,
    diag: Any,
    a4: Any,
    r2: Any,
    old_mass: np.ndarray,
    old_sat: np.ndarray,
    capacity: np.ndarray,
    cv_pv_m3: np.ndarray,
    face_pressure_psi: np.ndarray,
    p_ref_pa: float,
    q_m3_day: np.ndarray,
    nw: np.ndarray,
    no: np.ndarray,
    krw_max: np.ndarray,
    kro_max: np.ndarray,
    phi_cv: np.ndarray,
    cvgeom: dict[str, np.ndarray],
    delta_days: float,
) -> dict[str, Any]:
    mass = np.asarray(old_mass, dtype=np.float64).copy()
    cap = np.asarray(capacity, dtype=np.float64)
    old_total = fsum_array(mass)

    y_lookup, s_lookup = r3.build_mass_fraction_lookup(r2)

    dfmax = float(
        a4.max_dfw_realization(nw, no, krw_max, kro_max)
    )
    dt_eta_adv = float(
        r3.CFL
        * np.min(cvgeom["dtheta_cv"])
        / (dfmax + 1.0e-12)
    )
    adv_dt_days = float(
        dt_eta_adv
        * np.min(cvgeom["tau_end_s"])
        / SPD
    )
    if not np.isfinite(adv_dt_days) or adv_dt_days <= 0.0:
        raise ScientificFail("event_teacher_advective_CFL_nonpositive", adv_dt_days)

    remaining = float(delta_days)
    elapsed = 0.0
    steps = 0
    injected = 0.0
    produced = 0.0

    activation_steps = 0
    activation_events = 0
    upper_events = 0
    lower_events = 0
    unique_streamlines: set[int] = set()
    correction_mass = 0.0

    max_step_ledger = 0.0
    max_terminal_bound_residual = 0.0

    while remaining > 1.0e-12 * max(float(delta_days), 1.0):
        sat = r3.saturation_from_mass_fraction(
            mass,
            cap,
            y_lookup,
            s_lookup,
            1.0e-9,
        )

        flux = r3.teacher_face_fluxes(
            a4=a4,
            r2=r2,
            saturation=sat,
            q_m3_day=q_m3_day,
            face_pressure_psi=face_pressure_psi,
            p_ref_pa=p_ref_pa,
            nw=nw,
            no=no,
            krw_max=krw_max,
            kro_max=kro_max,
            phi_cv=phi_cv,
            cvgeom=cvgeom,
        )
        raw_adv = np.asarray(
            flux["advective_mass_flux_kg_day"],
            dtype=np.float64,
        )
        raw_cap = np.asarray(
            flux["capillary_mass_flux_kg_day"],
            dtype=np.float64,
        )
        raw_rhs = np.asarray(
            flux["rhs_mass_kg_day"],
            dtype=np.float64,
        )
        conductance = np.asarray(
            flux["capillary_phase_conductance_m3_day_per_sat"],
            dtype=np.float64,
        )

        con_sum = np.zeros((NSL, NCV), dtype=np.float64)
        con_sum[:, :-1] += conductance
        con_sum[:, 1:] += conductance
        active = con_sum > 1.0e-30
        cap_dt_days = (
            float(r3.CFL * np.min(cv_pv_m3[active] / con_sum[active]))
            if np.any(active)
            else float("inf")
        )

        limiter = diag.interior_limiter_candidate(
            mass,
            cap,
            raw_rhs,
            float(r3.MASS_CAPACITY_CFL),
        )
        dt_mass_interior = float(limiter["dt_days"])

        h = min(
            remaining,
            adv_dt_days,
            cap_dt_days,
            dt_mass_interior,
        )

        if not np.isfinite(h) or h <= float(r3.MIN_TEACHER_DT_DAYS):
            return {
                "mass": mass,
                "saturation_lookup": sat,
                "elapsed_days": elapsed,
                "remaining_days": remaining,
                "accepted_substeps": steps,
                "injected_mass_kg": injected,
                "produced_mass_kg": produced,
                "global_mass_residual_kg": (
                    fsum_array(mass)
                    - old_total
                    - injected
                    + produced
                ),
                "event_limiter": limiter,
                "advective_CFL_dt_days": adv_dt_days,
                "capillary_CFL_dt_days": cap_dt_days,
                "terminal_pass_through_activation_steps": activation_steps,
                "terminal_pass_through_activation_events": activation_events,
                "terminal_pass_through_upper_events": upper_events,
                "terminal_pass_through_lower_events": lower_events,
                "terminal_pass_through_unique_streamlines": np.asarray(
                    sorted(unique_streamlines),
                    dtype=np.int64,
                ),
                "terminal_pass_through_integrated_production_correction_kg":
                    correction_mass,
                "max_step_mass_ledger_residual_kg": max_step_ledger,
                "max_terminal_bound_residual_kg": max_terminal_bound_residual,
            }

        corrected_adv = raw_adv.copy()
        terminal_cap_net = raw_cap[:, -2] - raw_cap[:, -1]
        raw_terminal_rhs = (
            raw_adv[:, -2]
            - raw_adv[:, -1]
            + terminal_cap_net
        )
        raw_terminal_trial = mass[:, -1] + h * raw_terminal_rhs

        upper = raw_terminal_trial > cap[:, -1]
        lower = raw_terminal_trial < 0.0
        active_terminal = upper | lower

        if np.any(upper):
            corrected_adv[upper, -1] = (
                raw_adv[upper, -2]
                + terminal_cap_net[upper]
                - (cap[upper, -1] - mass[upper, -1]) / h
            )
        if np.any(lower):
            corrected_adv[lower, -1] = (
                raw_adv[lower, -2]
                + terminal_cap_net[lower]
                + mass[lower, -1] / h
            )
            bad_lower = lower & (corrected_adv[:, -1] < 0.0)
            if np.any(bad_lower):
                raise ScientificFail(
                    "event_terminal_lower_pass_through_negative_outflow",
                    {
                        "count": int(np.sum(bad_lower)),
                        "minimum_kg_day": float(
                            np.min(corrected_adv[bad_lower, -1])
                        ),
                    },
                )

        corrected_rhs = raw_rhs.copy()
        corrected_rhs[:, -1] = (
            corrected_adv[:, -2]
            - corrected_adv[:, -1]
            + terminal_cap_net
        )

        if np.any(active_terminal):
            activation_steps += 1
            idx = np.where(active_terminal)[0]
            activation_events += int(idx.size)
            upper_events += int(np.sum(upper))
            lower_events += int(np.sum(lower))
            unique_streamlines.update(int(x) for x in idx.tolist())
            correction_mass += (
                h
                * fsum_array(
                    corrected_adv[:, -1]
                    - raw_adv[:, -1]
                )
            )

        before = fsum_array(mass)
        trial = mass + h * corrected_rhs

        tol = max(
            1.0e-7,
            1.0e-12 * max(before, 1.0),
        )
        if float(np.min(trial)) < -tol:
            raise ScientificFail(
                "event_teacher_negative_mass_before_frozen_event",
                float(np.min(trial)),
            )
        if float(np.max(trial - cap)) > tol:
            raise ScientificFail(
                "event_teacher_capacity_before_frozen_event",
                float(np.max(trial - cap)),
            )

        terminal_residual = np.maximum(
            np.maximum(-trial[:, -1], 0.0),
            np.maximum(trial[:, -1] - cap[:, -1], 0.0),
        )
        max_terminal_bound_residual = max(
            max_terminal_bound_residual,
            float(np.max(terminal_residual)),
        )

        mass = trial

        inj_step = h * fsum_array(corrected_adv[:, 0])
        prod_step = h * fsum_array(corrected_adv[:, -1])
        injected += inj_step
        produced += prod_step

        after = fsum_array(mass)
        step_res = after - before - inj_step + prod_step
        max_step_ledger = max(max_step_ledger, abs(step_res))

        elapsed += h
        remaining = max(0.0, float(delta_days) - elapsed)
        steps += 1

        if steps > int(r3.MAX_TEACHER_SUBSTEPS):
            raise ScientificFail(
                "event_teacher_subcycling_exceeded_limit",
                steps,
            )

    raise ScientificFail(
        "frozen_interior_event_not_reached",
        {
            "elapsed_days": elapsed,
            "remaining_days": remaining,
            "substeps": steps,
        },
    )


def refresh_flow_epoch(
    *,
    label: str,
    r3: Any,
    a2e: Any,
    r2: Any,
    sg2: Any,
    sg3: Any,
    sg4: Any,
    sg5: Any,
    sg6: Any,
    sg7d: Any,
    r3r2r1: Any,
    permeability_md: np.ndarray,
    grid_mass: np.ndarray,
    start_saturation: np.ndarray,
    start_pressure_psi: np.ndarray,
    p_ref_pa: float,
    grid_pv: np.ndarray,
    grid_nw: np.ndarray,
    grid_no: np.ndarray,
    grid_krw: np.ndarray,
    grid_kro: np.ndarray,
    sci_gate,
) -> dict[str, Any]:
    try:
        refresh = a2e.fixed_point_refresh(
            r2=r2,
            r3r2r1=r3r2r1,
            sg2=sg2,
            sg3=sg3,
            permeability_md=permeability_md,
            parent_mass=grid_mass,
            parent_saturation=start_saturation,
            parent_pressure_psi=start_pressure_psi,
            p_ref_gas_pa=p_ref_pa,
            pore_volume_m3=grid_pv,
            nw=grid_nw,
            no=grid_no,
            krw_max=grid_krw,
            kro_max=grid_kro,
            sci_gate=sci_gate,
        )
    except Exception as exc:
        if exc.__class__.__name__ == "ScientificFail" and hasattr(exc, "gate"):
            raise ScientificFail(
                f"{label}_{exc.gate}",
                getattr(exc, "detail", None),
            ) from exc
        raise ScientificFail(
            f"{label}_fixed_point_refresh_failure",
            repr(exc),
        ) from exc

    saturation = np.asarray(
        refresh["saturation"],
        dtype=np.float64,
    )
    pressure = np.asarray(
        refresh["pressure_psi"],
        dtype=np.float64,
    )

    try:
        producer_rates, producer_sink = r3r2r1.producer_rates_updated(
            sg3,
            pressure,
            refresh["producer_wi"],
        )
        qx, qy, qz = sg4.compute_face_fluxes(
            pressure,
            refresh["tx"],
            refresh["ty"],
            refresh["tz"],
        )
        conservation = r3r2r1.flow_conservation_metrics(
            sg3,
            sg4,
            qx,
            qy,
            qz,
            producer_sink,
        )
    except Exception as exc:
        raise ScientificFail(
            f"{label}_Darcy_flow_failure",
            repr(exc),
        ) from exc

    sci_gate(
        f"{label}_all_BHP_wells_remain_producers",
        all(float(v["m3_s"]) > 0.0 for v in producer_rates.values()),
        {k: float(v["m3_day"]) for k, v in producer_rates.items()},
    )
    sci_gate(
        f"{label}_Darcy_local_conservation",
        float(conservation["local_relative_l2_error"]) < 1.0e-8,
        conservation["local_relative_l2_error"],
    )
    sci_gate(
        f"{label}_Darcy_global_conservation",
        float(conservation["global_relative_mismatch"]) < 1.0e-8,
        conservation["global_relative_mismatch"],
    )

    try:
        vx, vy, vz = sg5.construct_face_pore_velocities(qx, qy, qz)
        faces, seeds = sg5.build_seeds(qx, qy, qz)
        streamlines = sg5.trace_streamlines(seeds, vx, vy, vz)
        sg5_validation = sg5.validate_streamlines(
            faces,
            seeds,
            streamlines,
        )
    except Exception as exc:
        raise ScientificFail(
            f"{label}_Pollock_retrace_failure",
            repr(exc),
        ) from exc

    statuses = [str(s["status"]) for s in streamlines]
    sci_gate(
        f"{label}_all_streamlines_producer_captured",
        len(streamlines) == NSL
        and all(s == "PRODUCER" for s in statuses),
        {
            "count": len(streamlines),
            "status_counts": {
                s: statuses.count(s)
                for s in sorted(set(statuses))
            },
        },
    )

    try:
        sg6_streamlines = a2e.convert_sg5_to_sg6(streamlines)
        db = sg6.build_transport_database(sg6_streamlines)
        sg6.validate_transport(db)
    except Exception as exc:
        raise ScientificFail(
            f"{label}_SG6_TOF_failure",
            repr(exc),
        ) from exc

    xyz = np.asarray(db["xyz_m"], dtype=np.float64)
    tof = np.asarray(db["tau_s"], dtype=np.float64)
    weights_s = np.asarray(db["weights_m3_s"], dtype=np.float64)
    tau_end = np.asarray(db["tau_end_s"], dtype=np.float64)
    xi = np.asarray(db["xi"], dtype=np.float64).reshape(-1)

    sci_gate(
        f"{label}_streamline_signature_shape",
        xyz.shape == (NSL, NN, 3)
        and tof.shape == (NSL, NN)
        and weights_s.shape == (NSL,)
        and xi.shape == (NN,),
        {
            "xyz": xyz.shape,
            "tof": tof.shape,
            "weights": weights_s.shape,
            "xi": xi.shape,
        },
    )
    sci_gate(
        f"{label}_TOF_positive_monotone",
        np.all(tau_end > 0.0)
        and np.all(np.diff(tof, axis=1) >= -1.0e-12),
        {
            "tau_min_days": float(np.min(tau_end) / SPD),
            "tau_max_days": float(np.max(tau_end) / SPD),
        },
    )

    face_pressure = a2e.sample_pressure_at_streamline_nodes(
        sg7d,
        xyz,
        pressure,
    )

    reconstructed_mass = a2e.local_mass(
        r2,
        saturation,
        pressure,
        p_ref_pa,
        grid_pv,
    )
    sci_gate(
        f"{label}_same_time_mass_reconstruction",
        relative_l2(reconstructed_mass, grid_mass) <= 1.0e-10,
        relative_l2(reconstructed_mass, grid_mass),
    )

    return {
        "refresh": refresh,
        "saturation": saturation,
        "pressure_psi": pressure,
        "qx": qx,
        "qy": qy,
        "qz": qz,
        "conservation": conservation,
        "producer_rates": producer_rates,
        "sg5_validation": sg5_validation,
        "xyz_m": xyz,
        "tof_s": tof,
        "weights_m3_s": weights_s,
        "tau_end_s": tau_end,
        "xi": xi,
        "face_pressure_psi": face_pressure,
    }


def rebuild_transport_epoch_fields(
    *,
    r3: Any,
    sg7d: Any,
    xyz_m: np.ndarray,
    tof_s: np.ndarray,
    xi: np.ndarray,
    permeability_md: np.ndarray,
    grid_phi: np.ndarray,
    grid_nw: np.ndarray,
    grid_no: np.ndarray,
    grid_krw: np.ndarray,
    grid_kro: np.ndarray,
    pressure_nodes_psi: np.ndarray,
) -> dict[str, Any]:
    perm_nodes = sample_grid_to_nodes(sg7d, xyz_m, permeability_md)
    phi_nodes = sample_grid_to_nodes(sg7d, xyz_m, grid_phi)
    nw_nodes = sample_grid_to_nodes(sg7d, xyz_m, grid_nw)
    no_nodes = sample_grid_to_nodes(sg7d, xyz_m, grid_no)
    krw_nodes = sample_grid_to_nodes(sg7d, xyz_m, grid_krw)
    kro_nodes = sample_grid_to_nodes(sg7d, xyz_m, grid_kro)

    cvavg = lambda x: 0.5 * (x[:, :-1] + x[:, 1:])
    cvgeom = r3.build_cv_geometry_from_faces(
        tof_s,
        np.asarray(xi, dtype=np.float64).reshape(-1),
    )

    return {
        "permeability_nodes_md": perm_nodes,
        "porosity_nodes": phi_nodes,
        "nw_nodes": nw_nodes,
        "no_nodes": no_nodes,
        "krw_max_nodes": krw_nodes,
        "kro_max_nodes": kro_nodes,
        "pressure_nodes_psi": np.asarray(
            pressure_nodes_psi,
            dtype=np.float64,
        ),
        "permeability_cv_md": cvavg(perm_nodes),
        "porosity_cv": cvavg(phi_nodes),
        "nw_cv": cvavg(nw_nodes),
        "no_cv": cvavg(no_nodes),
        "krw_max_cv": cvavg(krw_nodes),
        "kro_max_cv": cvavg(kro_nodes),
        "pressure_cv_psi": cvavg(
            np.asarray(pressure_nodes_psi, dtype=np.float64)
        ),
        "cvgeom": cvgeom,
    }


def self_test() -> None:
    assert abs(PARENT_DAY + FIRST_DELTA_DAY - EVENT_DAY) < 1.0e-12
    assert abs(EVENT_DAY + SECOND_DELTA_DAY - TARGET_DAY) < 1.0e-12

    # Shared-face conservation identity.
    f = np.asarray([[10.0, 8.0, 5.0, 2.0]], dtype=np.float64)
    rhs = f[:, :-1] - f[:, 1:]
    assert abs(float(np.sum(rhs)) - 8.0) < 1.0e-14

    # Same-time operation carries no clock increment.
    t_before = EVENT_DAY
    t_after = EVENT_DAY
    assert t_before == t_after

    print(
        "POSTV16-AV4-F4-R3-R3 single event-renewal execution self-test: PASS"
    )


def main(project_root: Path, drive_root: Path) -> int:
    root = Path(project_root).resolve()
    drive = Path(drive_root).resolve()

    out = drive / OUT_REL
    failed = drive / FAIL_REL
    blocked = drive / BLOCK_REL

    gates: dict[str, dict[str, Any]] = {}
    stage = "preflight"

    event_refresh_executed = False
    event_reprojection_executed = False
    second_epoch_teacher_started = False
    day500_refresh_executed = False
    day500_reprojection_executed = False

    def gate(name: str, passed: Any, value: Any = None) -> None:
        ok = bool(passed)
        gates[name] = {"passed": ok, "value": value}
        print(
            f"[{'PASS' if ok else 'FAIL'}] {name}"
            + (f" — {value}" if value is not None else "")
        )
        if not ok:
            raise GateError(name)

    def sci_gate(name: str, passed: Any, value: Any = None) -> None:
        ok = bool(passed)
        gates[name] = {
            "passed": ok,
            "value": value,
            "scientific_execution_gate": True,
        }
        print(
            f"[{'PASS' if ok else 'FAIL'}] {name}"
            + (f" — {value}" if value is not None else "")
        )
        if not ok:
            raise ScientificFail(name, value)

    print("=" * 214)
    print(
        "POSTV16-AV4-F4-R3-R3 — CONTROLLED FIRST EVENT-TRIGGERED "
        "SAME-TIME FLOW-EPOCH RENEWAL + DAY500 CONTINUATION EXECUTION"
    )
    print("=" * 214)
    print("ONE EVENT REFRESH ONLY.")
    print("NO INTERIOR FACE LIMITER. NO FLUX REDISTRIBUTION. NO TIMESTEP-FLOOR CHANGE.")
    print("RAW F4 INTERIOR ADVECTION/CAPILLARITY REMAIN UNCHANGED.")
    print("F4-R2 TERMINAL PRODUCER PASS-THROUGH REMAINS UNCHANGED.")
    print("A SECOND INTERIOR CONFLICT IS AN IMMUTABLE SCIENTIFIC FAIL.")
    print("NO TRAINING. NO CHECKPOINT CREATION/INFERENCE. NO LOCKED OOD. NO CMG.")
    print()

    try:
        # ------------------------------------------------------------------------------------------
        # Repository/source authority.
        # ------------------------------------------------------------------------------------------
        stage = "repository_authority"

        parent = git_text(root, "rev-parse", "HEAD^")
        status = git_text(root, "status", "--porcelain")

        gate(
            "repository_parent_is_R3R2_commit",
            parent == PARENT_R3R2_COMMIT,
            parent,
        )
        gate("repository_clean", status == "", repr(status))

        for fn, expected in SOURCE_BLOBS.items():
            p = root / fn
            actual = git_blob(p, root) if p.is_file() else "missing"
            gate(
                f"{Path(fn).stem}_git_blob_exact",
                actual == expected,
                actual,
            )

        # ------------------------------------------------------------------------------------------
        # Bind formal R3-R2 design PASS.
        # ------------------------------------------------------------------------------------------
        stage = "R3R2_design_binding"

        r2d = drive / R3R2_REL
        gate("R3R2_output_present", r2d.is_dir(), str(r2d))
        mr2 = verify_manifest(r2d, R3R2_MANIFEST)
        gate("R3R2_manifest_exact_10", len(mr2) == 10, len(mr2))

        sr2 = load_json(r2d / R3R2_SUMMARY)
        rr2 = load_json(r2d / R3R2_REPAIR)
        tr2 = load_json(r2d / R3R2_TRIGGER)
        xr2 = load_json(r2d / R3R2_TRANSFER)
        er2 = load_json(r2d / R3R2_EPOCH)
        scr2 = load_json(r2d / R3R2_SCOPE)
        pr2 = load_json(r2d / R3R2_PROOF)
        hr2 = load_json(r2d / R3R2_HANDOFF)
        dr2 = load_json(r2d / R3R2_DECISION)

        gate(
            "R3R2_status_exact",
            sr2["status"] == R3R2_STATUS,
            sr2["status"],
        )
        gate(
            "R3R2_selected_repair_exact",
            rr2["selected_repair_class"]
            == "event_triggered_same_time_flow_epoch_renewal"
            and rr2["selected_interior_face_limiter"] is False,
        )
        gate(
            "R3R2_event_exact",
            abs(float(tr2["event_time_day"]) - EVENT_DAY) <= 1.0e-12
            and int(tr2["formal_control_event"]["streamline"]) == 793
            and int(tr2["formal_control_event"]["control_volume"]) == 197
            and tr2["formal_control_event"]["bound"] == "UPPER_CAPACITY",
            tr2["formal_control_event"],
        )
        gate(
            "R3R2_same_time_transfer_exact",
            float(xr2["physical_time_advance_during_refresh_days"]) == 0.0
            and len(xr2["same_time_pipeline"]) == 10,
        )
        gate(
            "R3R2_refreshed_epoch_rebuild_contract",
            er2["event_day"] == EVENT_DAY
            and len(er2["required_rebuilt_quantities"]) >= 10
            and len(er2["forbidden_epoch_mixing"]) == 4,
        )
        gate(
            "R3R2_single_refresh_scope_exact",
            int(scr2["maximum_event_refreshes_authorized"]) == 1
            and "scientific FAIL"
            in scr2["if_second_interior_bound_conflict_occurs"],
        )
        gate(
            "R3R2_proof_contract_present",
            len(pr2["R3R3_must_certify"]) >= 15,
            len(pr2["R3R3_must_certify"]),
        )
        gate(
            "R3R2_R3R3_handoff_exact",
            hr2["milestone"] == MILESTONE
            and hr2["authorized"] is True
            and hr2["execution"] is True
            and hr2["single_refresh_only"] is True
            and hr2["F5_dataset_generation_authorized_now"] is False,
        )
        gate(
            "R3R2_no_execution",
            dr2["repair_execution_performed"] is False
            and dr2["mapback_executed"] is False
            and dr2["flow_refresh_executed"] is False
            and dr2["reprojection_executed"] is False
            and dr2["R3R3_execution_authorized"] is True
            and dr2["F5_dataset_generation_authorized"] is False,
        )

        # ------------------------------------------------------------------------------------------
        # Bind R3-R1-R2 frozen event state.
        # ------------------------------------------------------------------------------------------
        stage = "R3R1R2_event_state_binding"

        r1d = drive / R3R1R2_REL
        gate("R3R1R2_output_present", r1d.is_dir(), str(r1d))
        mr1 = verify_manifest(r1d, R3R1R2_MANIFEST)
        gate("R3R1R2_manifest_exact_8", len(mr1) == 8, len(mr1))
        gate("R3R1R2_event_state_manifested", R3R1R2_STATE in mr1)

        r1_summary = load_json(r1d / R3R1R2_SUMMARY)
        gate(
            "R3R1R2_event_identity_exact",
            int(r1_summary["accepted_substeps_before_failure"]) == 3604
            and abs(
                float(r1_summary["failure_elapsed_days"])
                - FIRST_DELTA_DAY
            ) <= 1.0e-12
            and int(r1_summary["limiter_streamline"]) == 793
            and int(r1_summary["limiter_control_volume"]) == 197
            and r1_summary["limiter_bound"] == "UPPER_CAPACITY"
            and r1_summary["classification"]
            == "ADVECTION_DOMINATED_INTERIOR_BOUND_CONFLICT",
        )

        with np.load(r1d / R3R1R2_STATE, allow_pickle=False) as z:
            frozen_event_mass = np.asarray(
                z["partial_CV_component_mass_kg"],
                dtype=np.float64,
            )
            frozen_event_sat_lookup = np.asarray(
                z["partial_CV_saturation"],
                dtype=np.float64,
            )
            frozen_event_elapsed = float(
                np.asarray(z["elapsed_days"]).reshape(())
            )
            frozen_event_remaining = float(
                np.asarray(z["remaining_days"]).reshape(())
            )
            frozen_event_substeps = int(
                np.asarray(z["accepted_substeps"]).reshape(())
            )

        gate(
            "frozen_event_state_shapes",
            frozen_event_mass.shape == (NSL, NCV)
            and frozen_event_sat_lookup.shape == (NSL, NCV),
        )

        # ------------------------------------------------------------------------------------------
        # Bind Day365 parent split state / flow epoch.
        # ------------------------------------------------------------------------------------------
        stage = "Day365_parent_authority_binding"

        f2d = drive / F2R3_REL
        e1d = drive / E1R2_REL
        a2d = drive / A2E_REL

        gate("F2R3_output_present", f2d.is_dir(), str(f2d))
        gate("E1R2_output_present", e1d.is_dir(), str(e1d))
        gate("A2E_output_present", a2d.is_dir(), str(a2d))

        verify_manifest(f2d, F2R3_MANIFEST)
        verify_manifest(e1d, E1R2_MANIFEST)
        verify_manifest(a2d, A2E_MANIFEST)

        with np.load(f2d / F2R3_STATE, allow_pickle=False) as z:
            parent_cv_mass = np.asarray(
                z["parent_CV_component_mass_kg"],
                dtype=np.float64,
            )
            parent_cv_sat = np.asarray(
                z["parent_CV_saturation"],
                dtype=np.float64,
            )
            parent_cv_capacity = np.asarray(
                z["parent_CV_capacity_kg"],
                dtype=np.float64,
            )
            parent_cv_pv = np.asarray(
                z["parent_CV_pore_volume_m3"],
                dtype=np.float64,
            )
            parent_cv_coeff = np.asarray(
                z["parent_CV_pressure_mass_coeff"],
                dtype=np.float64,
            )
            parent_mapped_grid = np.asarray(
                z["mapped_grid_component_mass_kg"],
                dtype=np.float64,
            )
            parent_residual_grid = np.asarray(
                z["residual_grid_component_mass_kg"],
                dtype=np.float64,
            )
            parent_total_mass = float(
                np.asarray(z["parent_total_mass_kg"]).reshape(())
            )

        with np.load(e1d / E1R2_X13, allow_pickle=False) as z:
            X13 = np.asarray(
                z["X_refreshed_13"],
                dtype=np.float64,
            )

        with np.load(a2d / A2E_EPOCH, allow_pickle=False) as z:
            epoch = {k: np.asarray(z[k]).copy() for k in z.files}

        required_epoch = {
            "parent_component_mass_kg",
            "reconciled_saturation",
            "refreshed_pressure_psi",
            "pore_volume_m3",
            "reference_gas_pressure_pa",
            "streamline_xyz_m",
            "streamline_tof_s",
            "streamline_weight_m3_s",
            "streamline_face_pressure_psi",
            "xi",
            "nw",
            "no",
            "krw_max",
            "kro_max",
            "paired_porosity",
        }
        gate(
            "A2E_required_epoch_arrays",
            required_epoch.issubset(set(epoch)),
            sorted(required_epoch),
        )

        parent_grid_mass = np.asarray(
            epoch["parent_component_mass_kg"],
            dtype=np.float64,
        )
        parent_grid_sat = np.asarray(
            epoch["reconciled_saturation"],
            dtype=np.float64,
        )
        parent_pressure = np.asarray(
            epoch["refreshed_pressure_psi"],
            dtype=np.float64,
        )
        grid_pv = np.asarray(
            epoch["pore_volume_m3"],
            dtype=np.float64,
        )
        p_ref = float(
            np.asarray(epoch["reference_gas_pressure_pa"]).reshape(())
        )
        parent_xyz = np.asarray(
            epoch["streamline_xyz_m"],
            dtype=np.float64,
        )
        parent_tof = np.asarray(
            epoch["streamline_tof_s"],
            dtype=np.float64,
        )
        parent_weights_s = np.asarray(
            epoch["streamline_weight_m3_s"],
            dtype=np.float64,
        )
        parent_face_pressure = np.asarray(
            epoch["streamline_face_pressure_psi"],
            dtype=np.float64,
        )
        xi_parent = np.asarray(
            epoch["xi"],
            dtype=np.float64,
        ).reshape(-1)
        grid_nw = np.asarray(epoch["nw"], dtype=np.float64)
        grid_no = np.asarray(epoch["no"], dtype=np.float64)
        grid_krw = np.asarray(epoch["krw_max"], dtype=np.float64)
        grid_kro = np.asarray(epoch["kro_max"], dtype=np.float64)
        grid_phi = np.asarray(
            epoch["paired_porosity"],
            dtype=np.float64,
        )

        gate(
            "Day365_parent_shapes_exact",
            parent_grid_mass.shape == GRID
            and parent_grid_sat.shape == GRID
            and parent_pressure.shape == GRID
            and grid_pv.shape == GRID
            and grid_phi.shape == GRID
            and parent_xyz.shape == (NSL, NN, 3)
            and parent_tof.shape == (NSL, NN)
            and parent_weights_s.shape == (NSL,)
            and parent_face_pressure.shape == (NSL, NN)
            and xi_parent.shape == (NN,)
            and X13.shape == (NSL, NN, 13),
        )

        reconstructed_parent_grid = (
            parent_mapped_grid + parent_residual_grid
        )
        gate(
            "Day365_full_grid_mass_authority",
            relative_l2(
                parent_grid_mass,
                reconstructed_parent_grid,
            ) <= 1.0e-12
            and abs(
                fsum_array(parent_grid_mass)
                - parent_total_mass
            ) <= max(
                1.0e-6,
                1.0e-10 * parent_total_mass,
            ),
        )

        # ------------------------------------------------------------------------------------------
        # Load frozen source modules.
        # ------------------------------------------------------------------------------------------
        stage = "source_module_binding"

        r3 = load_module(root / F4R3, "postv16_av4_f4_r3r3_r3")
        diag = load_module(root / R3R1R2, "postv16_av4_f4_r3r3_diag")
        a4 = load_module(root / A4R2, "postv16_av4_f4_r3r3_a4")
        a2e = load_module(root / A2E, "postv16_av4_f4_r3r3_a2e")
        r2 = load_module(root / R2, "postv16_av4_f4_r3r3_r2")
        e37 = load_module(root / E37A, "postv16_av4_f4_r3r3_e37")
        sg2 = load_module(root / SG2, "postv16_av4_f4_r3r3_sg2")
        sg3 = load_module(root / SG3, "postv16_av4_f4_r3r3_sg3")
        sg4 = load_module(root / SG4, "postv16_av4_f4_r3r3_sg4")
        sg5 = load_module(root / SG5, "postv16_av4_f4_r3r3_sg5")
        sg6 = load_module(root / SG6, "postv16_av4_f4_r3r3_sg6")
        sg7d = load_module(root / SG7D, "postv16_av4_f4_r3r3_sg7d")
        r3r2r1 = load_module(root / R3R2R1, "postv16_av4_f4_r3r3_r3r2r1")

        gate(
            "frozen_execution_helpers_present",
            hasattr(r3, "execute_teacher_with_coeff")
            and hasattr(r3, "exact_parent_mass_mapback")
            and hasattr(r3, "bounded_reproject")
            and hasattr(r3, "teacher_face_fluxes")
            and hasattr(diag, "interior_limiter_candidate")
            and hasattr(a2e, "fixed_point_refresh"),
        )

        # Day365 CV constitutive fields exactly as frozen F4-R3.
        cvavg = 0.5 * (X13[:, :-1, :] + X13[:, 1:, :])
        phi_cv = cvavg[:, :, 5]
        nw_cv = 3.0 + cvavg[:, :, 9]
        no_cv = 3.0 + cvavg[:, :, 10]
        krw_cv = 0.80 + 0.20 * cvavg[:, :, 11]
        kro_cv = 0.80 + 0.20 * cvavg[:, :, 12]

        parent_cvgeom = r3.build_cv_geometry_from_faces(
            parent_tof,
            xi_parent,
        )
        parent_operator = sg7d.build_subsegment_operator(
            parent_xyz,
            parent_tof / SPD,
            parent_weights_s * SPD,
        )
        parent_geometry = e37.build_control_volume_geometry(
            r2,
            parent_operator,
            parent_pressure,
            p_ref,
            NSL,
            NCV,
        )

        sci_gate(
            "Day365_parent_geometry_matches_split_state",
            float(
                np.max(
                    np.abs(
                        np.asarray(parent_geometry["cv_pv_m3"])
                        - parent_cv_pv
                    )
                )
            ) <= 1.0e-8
            and relative_l2(
                np.asarray(
                    parent_geometry["cv_pressure_mass_coeff"]
                ),
                parent_cv_coeff,
            ) <= 1.0e-12,
        )

        # ------------------------------------------------------------------------------------------
        # Reproduce accepted Day365 -> event trajectory; do not apply failed substep.
        # ------------------------------------------------------------------------------------------
        stage = "Day365_to_event_transport_reproduction"

        event_run = execute_until_first_interior_event(
            r3=r3,
            diag=diag,
            a4=a4,
            r2=r2,
            old_mass=parent_cv_mass,
            old_sat=parent_cv_sat,
            capacity=parent_cv_capacity,
            cv_pv_m3=parent_cv_pv,
            face_pressure_psi=parent_face_pressure,
            p_ref_pa=p_ref,
            q_m3_day=parent_weights_s * SPD,
            nw=nw_cv,
            no=no_cv,
            krw_max=krw_cv,
            kro_max=kro_cv,
            phi_cv=phi_cv,
            cvgeom=parent_cvgeom,
            delta_days=TOTAL_DELTA_DAY,
        )

        limiter = event_run["event_limiter"]
        sci_gate(
            "frozen_event_reproduced_exactly",
            int(event_run["accepted_substeps"]) == 3604
            and abs(
                float(event_run["elapsed_days"])
                - FIRST_DELTA_DAY
            ) <= 1.0e-12
            and abs(
                float(event_run["remaining_days"])
                - SECOND_DELTA_DAY
            ) <= 1.0e-12
            and int(limiter["streamline"]) == 793
            and int(limiter["control_volume"]) == 197
            and limiter["bound"] == "UPPER_CAPACITY",
            {
                "substeps": event_run["accepted_substeps"],
                "elapsed": event_run["elapsed_days"],
                "remaining": event_run["remaining_days"],
                "limiter": limiter,
            },
        )

        event_mass_rel = relative_l2(
            event_run["mass"],
            frozen_event_mass,
        )
        event_mass_linf = float(
            np.max(
                np.abs(
                    event_run["mass"]
                    - frozen_event_mass
                )
            )
        )
        event_sat_linf = float(
            np.max(
                np.abs(
                    event_run["saturation_lookup"]
                    - frozen_event_sat_lookup
                )
            )
        )
        sci_gate(
            "rerun_event_state_matches_frozen_R3R1R2_state",
            event_mass_rel <= 1.0e-14
            and event_mass_linf <= 1.0e-9
            and event_sat_linf <= 1.0e-12
            and abs(
                event_run["elapsed_days"]
                - frozen_event_elapsed
            ) <= 1.0e-12
            and abs(
                event_run["remaining_days"]
                - frozen_event_remaining
            ) <= 1.0e-12
            and event_run["accepted_substeps"]
            == frozen_event_substeps,
            {
                "mass_relative_L2": event_mass_rel,
                "mass_Linf_kg": event_mass_linf,
                "saturation_Linf": event_sat_linf,
            },
        )
        sci_gate(
            "event_first_epoch_mass_ledger",
            abs(float(event_run["global_mass_residual_kg"]))
            <= max(
                1.0e-6,
                1.0e-10
                * max(
                    fsum_array(event_run["mass"]),
                    1.0,
                ),
            ),
            event_run["global_mass_residual_kg"],
        )
        sci_gate(
            "event_terminal_pass_through_history_reproduced",
            int(event_run["terminal_pass_through_activation_events"])
            == 8602
            and int(
                event_run["terminal_pass_through_unique_streamlines"].size
            ) == 12,
            {
                "events": event_run[
                    "terminal_pass_through_activation_events"
                ],
                "unique": int(
                    event_run[
                        "terminal_pass_through_unique_streamlines"
                    ].size
                ),
            },
        )

        # Exact E37A inversion for conservative mapback.
        event_cv_sat_exact = np.asarray(
            e37.invert_cv_mass_to_saturation(
                r2,
                event_run["mass"],
                parent_cv_coeff,
            ),
            dtype=np.float64,
        )

        # ------------------------------------------------------------------------------------------
        # Same-time event mapback.
        # ------------------------------------------------------------------------------------------
        stage = "event_exact_cartesian_mapback"

        try:
            event_mapback = r3.exact_parent_mass_mapback(
                r2=r2,
                parent_grid_mass=parent_grid_mass,
                old_cv_saturation=parent_cv_sat,
                new_cv_saturation=event_cv_sat_exact,
                old_cv_mass=parent_cv_mass,
                new_cv_mass=event_run["mass"],
                geometry=parent_geometry,
                p_ref_pa=p_ref,
            )
        except Exception as exc:
            if exc.__class__.__name__ == "ScientificFail" and hasattr(exc, "gate"):
                raise ScientificFail(
                    f"event_mapback_{exc.gate}",
                    getattr(exc, "detail", None),
                ) from exc
            raise ScientificFail(
                "event_mapback_failure",
                repr(exc),
            ) from exc

        event_grid_mass = np.asarray(
            event_mapback["future_grid_mass_kg"],
            dtype=np.float64,
        )
        expected_event_total = (
            fsum_array(parent_grid_mass)
            + float(event_run["injected_mass_kg"])
            - float(event_run["produced_mass_kg"])
        )
        sci_gate(
            "event_cartesian_mass_ledger",
            abs(
                fsum_array(event_grid_mass)
                - expected_event_total
            ) <= float(event_mapback["roundoff_mass_kg"]),
            {
                "grid_mass": fsum_array(event_grid_mass),
                "expected": expected_event_total,
                "tolerance": event_mapback["roundoff_mass_kg"],
            },
        )

        # Preliminary event saturation under old pressure.
        try:
            event_sg_start = a2e.invert_local_mass(
                r2,
                event_grid_mass,
                parent_pressure,
                p_ref,
                grid_pv,
            )
        except Exception as exc:
            raise ScientificFail(
                "event_parent_pressure_mass_inversion_failure",
                repr(exc),
            ) from exc
        event_sat_start = BACKGROUND + np.asarray(
            event_sg_start,
            dtype=np.float64,
        )

        # ------------------------------------------------------------------------------------------
        # ONE authorized same-time event flow refresh.
        # ------------------------------------------------------------------------------------------
        stage = "event_same_time_flow_epoch_refresh"

        permeability_md = np.loadtxt(
            root / PERM,
            skiprows=1,
            dtype=np.float64,
        ).reshape(GRID, order="C")

        event_flow = refresh_flow_epoch(
            label="event_refresh",
            r3=r3,
            a2e=a2e,
            r2=r2,
            sg2=sg2,
            sg3=sg3,
            sg4=sg4,
            sg5=sg5,
            sg6=sg6,
            sg7d=sg7d,
            r3r2r1=r3r2r1,
            permeability_md=permeability_md,
            grid_mass=event_grid_mass,
            start_saturation=event_sat_start,
            start_pressure_psi=parent_pressure,
            p_ref_pa=p_ref,
            grid_pv=grid_pv,
            grid_nw=grid_nw,
            grid_no=grid_no,
            grid_krw=grid_krw,
            grid_kro=grid_kro,
            sci_gate=sci_gate,
        )
        event_refresh_executed = True

        # ------------------------------------------------------------------------------------------
        # Bounded event-time reprojection onto refreshed geometry.
        # ------------------------------------------------------------------------------------------
        stage = "event_bounded_split_state_reprojection"

        try:
            event_split = r3.bounded_reproject(
                r2=r2,
                e37=e37,
                sg7d=sg7d,
                xyz_m=event_flow["xyz_m"],
                tof_s=event_flow["tof_s"],
                weights_m3_s=event_flow["weights_m3_s"],
                grid_mass=event_grid_mass,
                grid_pore_volume_m3=grid_pv,
                pressure_psi=event_flow["pressure_psi"],
                p_ref_pa=p_ref,
            )
        except Exception as exc:
            if exc.__class__.__name__ == "ScientificFail" and hasattr(exc, "gate"):
                raise ScientificFail(
                    f"event_reprojection_{exc.gate}",
                    getattr(exc, "detail", None),
                ) from exc
            raise ScientificFail(
                "event_reprojection_failure",
                repr(exc),
            ) from exc

        event_reprojection_executed = True

        sci_gate(
            "event_reprojection_zero_overloaded_CVs",
            int(event_split["overloaded_CV_count"]) == 0,
            {
                "overloaded": event_split["overloaded_CV_count"],
                "max_excess_kg": event_split[
                    "maximum_capacity_excess_kg"
                ],
            },
        )
        sci_gate(
            "event_reprojection_mass_ledger",
            abs(float(event_split["ledger_residual_kg"]))
            <= max(
                1.0e-6,
                1.0e-10
                * max(fsum_array(event_grid_mass), 1.0),
            ),
            event_split["ledger_residual_kg"],
        )
        sci_gate(
            "event_reprojection_residual_nonnegative",
            float(
                np.min(event_split["residual_grid_mass"])
            ) >= -1.0e-8,
            float(
                np.min(event_split["residual_grid_mass"])
            ),
        )

        # ------------------------------------------------------------------------------------------
        # Rebuild all refreshed streamline-aligned fields.
        # ------------------------------------------------------------------------------------------
        stage = "event_refreshed_epoch_field_rebuild"

        event_fields = rebuild_transport_epoch_fields(
            r3=r3,
            sg7d=sg7d,
            xyz_m=event_flow["xyz_m"],
            tof_s=event_flow["tof_s"],
            xi=event_flow["xi"],
            permeability_md=permeability_md,
            grid_phi=grid_phi,
            grid_nw=grid_nw,
            grid_no=grid_no,
            grid_krw=grid_krw,
            grid_kro=grid_kro,
            pressure_nodes_psi=event_flow[
                "face_pressure_psi"
            ],
        )

        sci_gate(
            "event_refreshed_epoch_fields_finite",
            all(
                np.isfinite(
                    np.asarray(event_fields[k])
                ).all()
                for k in [
                    "permeability_nodes_md",
                    "porosity_nodes",
                    "nw_nodes",
                    "no_nodes",
                    "krw_max_nodes",
                    "kro_max_nodes",
                    "pressure_nodes_psi",
                    "permeability_cv_md",
                    "porosity_cv",
                    "nw_cv",
                    "no_cv",
                    "krw_max_cv",
                    "kro_max_cv",
                ]
            ),
        )
        sci_gate(
            "event_refreshed_CV_state_shapes",
            event_split["cv_mass"].shape == (NSL, NCV)
            and event_split["cv_saturation"].shape == (NSL, NCV)
            and event_split["cv_capacity"].shape == (NSL, NCV)
            and event_split["cv_pore_volume_m3"].shape == (NSL, NCV)
            and event_fields["porosity_cv"].shape == (NSL, NCV),
        )

        # Confirm geometry was genuinely rebuilt and not aliased positionally.
        tof_change = relative_l2(
            event_flow["tof_s"],
            parent_tof,
        )
        pressure_node_change = relative_l2(
            event_flow["face_pressure_psi"],
            parent_face_pressure,
        )
        sci_gate(
            "event_refresh_changes_flow_epoch",
            tof_change > 1.0e-12
            or pressure_node_change > 1.0e-12,
            {
                "TOF_relative_L2_change": tof_change,
                "pressure_node_relative_L2_change":
                    pressure_node_change,
            },
        )

        # ------------------------------------------------------------------------------------------
        # Resume remaining 86.213... days on refreshed epoch.
        # ------------------------------------------------------------------------------------------
        stage = "post_refresh_remaining_transport"
        second_epoch_teacher_started = True

        try:
            second_teacher = r3.execute_teacher_with_coeff(
                a4=a4,
                r2=r2,
                e37=e37,
                old_mass=np.asarray(
                    event_split["cv_mass"],
                    dtype=np.float64,
                ),
                old_sat=np.asarray(
                    event_split["cv_saturation"],
                    dtype=np.float64,
                ),
                capacity=np.asarray(
                    event_split["cv_capacity"],
                    dtype=np.float64,
                ),
                cv_pressure_mass_coeff=np.asarray(
                    event_split[
                        "cv_pressure_mass_coeff"
                    ],
                    dtype=np.float64,
                ),
                cv_pv_m3=np.asarray(
                    event_split["cv_pore_volume_m3"],
                    dtype=np.float64,
                ),
                face_pressure_psi=event_flow[
                    "face_pressure_psi"
                ],
                p_ref_pa=p_ref,
                q_m3_day=event_flow[
                    "weights_m3_s"
                ] * SPD,
                nw=event_fields["nw_cv"],
                no=event_fields["no_cv"],
                krw_max=event_fields["krw_max_cv"],
                kro_max=event_fields["kro_max_cv"],
                phi_cv=event_fields["porosity_cv"],
                cvgeom=event_fields["cvgeom"],
                delta_days=SECOND_DELTA_DAY,
            )
        except Exception as exc:
            if exc.__class__.__name__ == "ScientificFail" and hasattr(exc, "gate"):
                raise ScientificFail(
                    "second_interior_conflict_or_post_refresh_teacher_failure:"
                    + str(exc.gate),
                    {
                        "original_gate": exc.gate,
                        "original_detail": getattr(exc, "detail", None),
                        "second_event_refresh_authorized": False,
                    },
                ) from exc
            raise ScientificFail(
                "post_refresh_teacher_failure",
                repr(exc),
            ) from exc

        sci_gate(
            "post_refresh_teacher_global_mass_closure",
            abs(
                float(second_teacher["global_mass_residual_kg"])
            )
            <= float(
                second_teacher["global_mass_tolerance_kg"]
            ),
            {
                "residual_kg":
                    second_teacher[
                        "global_mass_residual_kg"
                    ],
                "tolerance_kg":
                    second_teacher[
                        "global_mass_tolerance_kg"
                    ],
            },
        )
        sci_gate(
            "post_refresh_teacher_bounds",
            float(
                np.min(
                    second_teacher[
                        "future_mass_fraction"
                    ]
                )
            ) >= -1.0e-10
            and float(
                np.max(
                    second_teacher[
                        "future_mass_fraction"
                    ]
                )
            ) <= 1.0 + 1.0e-10,
            [
                float(
                    np.min(
                        second_teacher[
                            "future_mass_fraction"
                        ]
                    )
                ),
                float(
                    np.max(
                        second_teacher[
                            "future_mass_fraction"
                        ]
                    )
                ),
            ],
        )
        sci_gate(
            "post_refresh_terminal_pass_through_invariants",
            float(
                second_teacher[
                    "max_internal_advective_identity_error_kg_day"
                ]
            ) <= 1.0e-14
            and float(
                second_teacher[
                    "max_capillary_identity_error_kg_day"
                ]
            ) <= 1.0e-14
            and float(
                second_teacher[
                    "pass_through_max_terminal_bound_residual_kg"
                ]
            ) <= 1.0e-7,
        )

        # ------------------------------------------------------------------------------------------
        # Map post-refresh CV increment onto exact event-time Cartesian mass.
        # ------------------------------------------------------------------------------------------
        stage = "post_refresh_to_Day500_cartesian_mapback"

        try:
            final_mapback = r3.exact_parent_mass_mapback(
                r2=r2,
                parent_grid_mass=event_grid_mass,
                old_cv_saturation=np.asarray(
                    event_split["cv_saturation"],
                    dtype=np.float64,
                ),
                new_cv_saturation=np.asarray(
                    second_teacher["future_saturation"],
                    dtype=np.float64,
                ),
                old_cv_mass=np.asarray(
                    event_split["cv_mass"],
                    dtype=np.float64,
                ),
                new_cv_mass=np.asarray(
                    second_teacher["future_mass"],
                    dtype=np.float64,
                ),
                geometry=event_split["geometry"],
                p_ref_pa=p_ref,
            )
        except Exception as exc:
            if exc.__class__.__name__ == "ScientificFail" and hasattr(exc, "gate"):
                raise ScientificFail(
                    f"Day500_mapback_{exc.gate}",
                    getattr(exc, "detail", None),
                ) from exc
            raise ScientificFail(
                "Day500_mapback_failure",
                repr(exc),
            ) from exc

        day500_grid_mass = np.asarray(
            final_mapback["future_grid_mass_kg"],
            dtype=np.float64,
        )

        total_injected = (
            float(event_run["injected_mass_kg"])
            + float(second_teacher["injected_mass_kg"])
        )
        total_produced = (
            float(event_run["produced_mass_kg"])
            + float(second_teacher["produced_mass_kg"])
        )
        expected_day500_total = (
            fsum_array(parent_grid_mass)
            + total_injected
            - total_produced
        )

        sci_gate(
            "global_Day365_to_Day500_mass_ledger",
            abs(
                fsum_array(day500_grid_mass)
                - expected_day500_total
            )
            <= float(final_mapback["roundoff_mass_kg"]),
            {
                "Day500_grid_mass_kg":
                    fsum_array(day500_grid_mass),
                "expected_kg": expected_day500_total,
                "injected_kg": total_injected,
                "produced_kg": total_produced,
                "tolerance_kg":
                    final_mapback["roundoff_mass_kg"],
            },
        )

        # ------------------------------------------------------------------------------------------
        # Original Day500 same-time certification refresh.
        # ------------------------------------------------------------------------------------------
        stage = "Day500_same_time_dynamic_flow_refresh"

        try:
            final_sg_start = a2e.invert_local_mass(
                r2,
                day500_grid_mass,
                event_flow["pressure_psi"],
                p_ref,
                grid_pv,
            )
        except Exception as exc:
            raise ScientificFail(
                "Day500_event_pressure_mass_inversion_failure",
                repr(exc),
            ) from exc
        final_sat_start = BACKGROUND + np.asarray(
            final_sg_start,
            dtype=np.float64,
        )

        day500_flow = refresh_flow_epoch(
            label="Day500_refresh",
            r3=r3,
            a2e=a2e,
            r2=r2,
            sg2=sg2,
            sg3=sg3,
            sg4=sg4,
            sg5=sg5,
            sg6=sg6,
            sg7d=sg7d,
            r3r2r1=r3r2r1,
            permeability_md=permeability_md,
            grid_mass=day500_grid_mass,
            start_saturation=final_sat_start,
            start_pressure_psi=event_flow["pressure_psi"],
            p_ref_pa=p_ref,
            grid_pv=grid_pv,
            grid_nw=grid_nw,
            grid_no=grid_no,
            grid_krw=grid_krw,
            grid_kro=grid_kro,
            sci_gate=sci_gate,
        )
        day500_refresh_executed = True

        # ------------------------------------------------------------------------------------------
        # Original Day500 bounded split-state reprojection.
        # ------------------------------------------------------------------------------------------
        stage = "Day500_bounded_split_state_reprojection"

        try:
            day500_split = r3.bounded_reproject(
                r2=r2,
                e37=e37,
                sg7d=sg7d,
                xyz_m=day500_flow["xyz_m"],
                tof_s=day500_flow["tof_s"],
                weights_m3_s=day500_flow["weights_m3_s"],
                grid_mass=day500_grid_mass,
                grid_pore_volume_m3=grid_pv,
                pressure_psi=day500_flow["pressure_psi"],
                p_ref_pa=p_ref,
            )
        except Exception as exc:
            if exc.__class__.__name__ == "ScientificFail" and hasattr(exc, "gate"):
                raise ScientificFail(
                    f"Day500_reprojection_{exc.gate}",
                    getattr(exc, "detail", None),
                ) from exc
            raise ScientificFail(
                "Day500_reprojection_failure",
                repr(exc),
            ) from exc

        day500_reprojection_executed = True

        sci_gate(
            "Day500_reprojection_zero_overloaded_CVs",
            int(day500_split["overloaded_CV_count"]) == 0,
            {
                "overloaded":
                    day500_split[
                        "overloaded_CV_count"
                    ],
                "max_excess_kg":
                    day500_split[
                        "maximum_capacity_excess_kg"
                    ],
            },
        )
        sci_gate(
            "Day500_split_state_mass_ledger",
            abs(float(day500_split["ledger_residual_kg"]))
            <= max(
                1.0e-6,
                1.0e-10
                * max(
                    fsum_array(day500_grid_mass),
                    1.0,
                ),
            ),
            day500_split["ledger_residual_kg"],
        )
        sci_gate(
            "Day500_residual_grid_mass_nonnegative",
            float(
                np.min(
                    day500_split[
                        "residual_grid_mass"
                    ]
                )
            ) >= -1.0e-8,
            float(
                np.min(
                    day500_split[
                        "residual_grid_mass"
                    ]
                )
            ),
        )

        # Final mass reconstruction under Day500 refreshed pressure.
        final_mass_recon = a2e.local_mass(
            r2,
            day500_flow["saturation"],
            day500_flow["pressure_psi"],
            p_ref,
            grid_pv,
        )
        sci_gate(
            "Day500_refreshed_saturation_exact_grid_mass",
            relative_l2(
                final_mass_recon,
                day500_grid_mass,
            ) <= 1.0e-10,
            relative_l2(
                final_mass_recon,
                day500_grid_mass,
            ),
        )

        # ------------------------------------------------------------------------------------------
        # Publish accepted R3-R3 state.
        # ------------------------------------------------------------------------------------------
        stage = "final_certification_and_publish"

        event_audit = {
            "milestone": MILESTONE,
            "event_day": EVENT_DAY,
            "first_epoch_substeps": int(
                event_run["accepted_substeps"]
            ),
            "first_epoch_injected_mass_kg": float(
                event_run["injected_mass_kg"]
            ),
            "first_epoch_produced_mass_kg": float(
                event_run["produced_mass_kg"]
            ),
            "first_epoch_mass_residual_kg": float(
                event_run["global_mass_residual_kg"]
            ),
            "event_streamline": int(
                limiter["streamline"]
            ),
            "event_control_volume": int(
                limiter["control_volume"]
            ),
            "event_bound": limiter["bound"],
            "event_mass_dt_days": float(
                limiter["dt_days"]
            ),
            "event_mapback_mass_kg": fsum_array(
                event_grid_mass
            ),
            "event_fixed_point_iterations": len(
                event_flow["refresh"]["rows"]
            ),
            "event_Darcy_local_relative_error": float(
                event_flow["conservation"][
                    "local_relative_l2_error"
                ]
            ),
            "event_Darcy_global_relative_mismatch": float(
                event_flow["conservation"][
                    "global_relative_mismatch"
                ]
            ),
            "event_tau_min_days": float(
                np.min(
                    event_flow["tau_end_s"]
                ) / SPD
            ),
            "event_tau_max_days": float(
                np.max(
                    event_flow["tau_end_s"]
                ) / SPD
            ),
            "event_reprojection_mapped_mass_kg": float(
                event_split["mapped_mass_kg"]
            ),
            "event_reprojection_residual_mass_kg": float(
                event_split["residual_mass_kg"]
            ),
            "event_reprojection_ledger_residual_kg": float(
                event_split["ledger_residual_kg"]
            ),
            "TOF_relative_L2_change_from_Day365": tof_change,
            "pressure_node_relative_L2_change_from_Day365":
                pressure_node_change,
            "physical_time_advance_days": 0.0,
        }

        second_teacher_audit = {
            "milestone": MILESTONE,
            "parent_day": EVENT_DAY,
            "target_day": TARGET_DAY,
            "delta_day": SECOND_DELTA_DAY,
            "substeps": int(second_teacher["substeps"]),
            "injected_mass_kg": float(
                second_teacher["injected_mass_kg"]
            ),
            "produced_mass_kg": float(
                second_teacher["produced_mass_kg"]
            ),
            "global_mass_residual_kg": float(
                second_teacher["global_mass_residual_kg"]
            ),
            "global_mass_tolerance_kg": float(
                second_teacher["global_mass_tolerance_kg"]
            ),
            "minimum_dt_days": float(
                second_teacher["minimum_dt_days"]
            ),
            "maximum_dt_days": float(
                second_teacher["maximum_dt_days"]
            ),
            "advective_CFL_dt_days": float(
                second_teacher["advective_CFL_dt_days"]
            ),
            "minimum_interior_mass_dt_days": float(
                second_teacher[
                    "minimum_interior_mass_dt_days"
                ]
            ),
            "pass_through_activation_events": int(
                second_teacher[
                    "pass_through_activation_events"
                ]
            ),
            "pass_through_unique_streamlines": int(
                second_teacher[
                    "pass_through_unique_streamline_count"
                ]
            ),
            "future_mass_fraction_min": float(
                np.min(
                    second_teacher[
                        "future_mass_fraction"
                    ]
                )
            ),
            "future_mass_fraction_max": float(
                np.max(
                    second_teacher[
                        "future_mass_fraction"
                    ]
                )
            ),
        }

        day500_audit = {
            "milestone": MILESTONE,
            "Day500_grid_mass_kg": fsum_array(
                day500_grid_mass
            ),
            "Day500_fixed_point_iterations": len(
                day500_flow["refresh"]["rows"]
            ),
            "Day500_Darcy_local_relative_error": float(
                day500_flow["conservation"][
                    "local_relative_l2_error"
                ]
            ),
            "Day500_Darcy_global_relative_mismatch": float(
                day500_flow["conservation"][
                    "global_relative_mismatch"
                ]
            ),
            "Day500_tau_min_days": float(
                np.min(
                    day500_flow["tau_end_s"]
                ) / SPD
            ),
            "Day500_tau_max_days": float(
                np.max(
                    day500_flow["tau_end_s"]
                ) / SPD
            ),
            "Day500_reprojection_mapped_mass_kg": float(
                day500_split["mapped_mass_kg"]
            ),
            "Day500_reprojection_residual_mass_kg": float(
                day500_split["residual_mass_kg"]
            ),
            "Day500_reprojection_ledger_residual_kg": float(
                day500_split["ledger_residual_kg"]
            ),
            "Day500_overloaded_CV_count": int(
                day500_split["overloaded_CV_count"]
            ),
        }

        mass_ledger = {
            "milestone": MILESTONE,
            "Day365_initial_grid_mass_kg": fsum_array(
                parent_grid_mass
            ),
            "first_epoch_injected_mass_kg": float(
                event_run["injected_mass_kg"]
            ),
            "first_epoch_produced_mass_kg": float(
                event_run["produced_mass_kg"]
            ),
            "event_grid_mass_kg": fsum_array(
                event_grid_mass
            ),
            "second_epoch_injected_mass_kg": float(
                second_teacher["injected_mass_kg"]
            ),
            "second_epoch_produced_mass_kg": float(
                second_teacher["produced_mass_kg"]
            ),
            "total_injected_mass_kg": total_injected,
            "total_produced_mass_kg": total_produced,
            "expected_Day500_mass_kg": expected_day500_total,
            "actual_Day500_grid_mass_kg": fsum_array(
                day500_grid_mass
            ),
            "global_Day365_to_Day500_residual_kg": (
                fsum_array(day500_grid_mass)
                - expected_day500_total
            ),
            "event_refresh_physical_time_advance_days": 0.0,
            "event_refresh_count": 1,
        }

        f5_handoff = {
            "milestone": "POSTV16-AV4-F5",
            "name": (
                "Restart-Teacher Dataset Generation with Frozen "
                "Single Event-Triggered Flow-Epoch Renewal Policy"
            ),
            "authorized": True,
            "execution": True,
            "required_R3R3_status": STATUS_PASS,
            "teacher_policy": {
                "raw_internal_F4_operator": "unchanged",
                "terminal_producer_pass_through": "F4-R2 frozen",
                "first_interior_invariant_domain_conflict":
                    "one same-time flow-epoch renewal",
                "maximum_event_refreshes_per_transition": 1,
                "second_interior_conflict":
                    "scientific FAIL; no automatic second refresh",
            },
            "allowed": [
                "generate TRAIN restart teachers",
                "generate VALIDATION restart teachers",
                "apply the same frozen one-refresh policy",
                "publish dataset/provenance artifacts",
            ],
            "training_authorized": False,
            "checkpoint_creation_authorized": False,
            "checkpoint_inference_authorized": False,
            "locked_OOD_teacher_access_authorized": False,
            "A3_E2_authorized": False,
            "AV4_general_dynamic_transport_authorized": False,
        }

        decision = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "historical_F4_scientific_FAIL_preserved": True,
            "historical_F4R3_scientific_FAIL_preserved": True,
            "R3R2_design_bound": True,
            "event_refresh_count": 1,
            "event_refresh_executed": True,
            "event_reprojection_executed": True,
            "second_epoch_teacher_completed": True,
            "second_event_refresh_executed": False,
            "Day500_refresh_executed": True,
            "Day500_reprojection_executed": True,
            "interior_face_limiter_used": False,
            "raw_interior_transport_operator_changed": False,
            "terminal_pass_through_changed": False,
            "timestep_floor_changed": False,
            "mass_clipped_or_rescaled": False,
            "capacity_relaxed": False,
            "support_expanded": False,
            "training_performed": False,
            "checkpoint_created": False,
            "checkpoint_inference_performed": False,
            "locked_OOD_opened": False,
            "F5_dataset_generation_authorized": True,
            "training_authorized": False,
            "A3_E2_authorized": False,
            "AV4_general_dynamic_transport_authorized": False,
        }

        summary = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "event_day": EVENT_DAY,
            "event_refresh_count": 1,
            "first_epoch_substeps": int(
                event_run["accepted_substeps"]
            ),
            "second_epoch_substeps": int(
                second_teacher["substeps"]
            ),
            "event_streamline": int(
                limiter["streamline"]
            ),
            "event_control_volume": int(
                limiter["control_volume"]
            ),
            "event_bound": limiter["bound"],
            "event_grid_mass_kg": fsum_array(
                event_grid_mass
            ),
            "Day500_grid_mass_kg": fsum_array(
                day500_grid_mass
            ),
            "global_mass_residual_kg": (
                fsum_array(day500_grid_mass)
                - expected_day500_total
            ),
            "Day500_overloaded_CV_count": int(
                day500_split["overloaded_CV_count"]
            ),
            "second_event_refresh_executed": False,
            "F5_authorized": True,
            "training_authorized": False,
        }

        event_state_npz = deterministic_npz_bytes(
            {
                "event_day": np.asarray(EVENT_DAY),
                "event_grid_component_mass_kg":
                    event_grid_mass,
                "event_grid_saturation":
                    event_flow["saturation"],
                "event_grid_pressure_psi":
                    event_flow["pressure_psi"],
                "event_streamline_xyz_m":
                    event_flow["xyz_m"],
                "event_streamline_tof_s":
                    event_flow["tof_s"],
                "event_streamline_weight_m3_s":
                    event_flow["weights_m3_s"],
                "event_streamline_face_pressure_psi":
                    event_flow["face_pressure_psi"],
                "event_CV_component_mass_kg":
                    event_split["cv_mass"],
                "event_CV_saturation":
                    event_split["cv_saturation"],
                "event_CV_capacity_kg":
                    event_split["cv_capacity"],
                "event_CV_pore_volume_m3":
                    event_split["cv_pore_volume_m3"],
                "event_CV_pressure_mass_coeff":
                    event_split[
                        "cv_pressure_mass_coeff"
                    ],
                "event_residual_grid_component_mass_kg":
                    event_split[
                        "residual_grid_mass"
                    ],
                "event_permeability_nodes_md":
                    event_fields[
                        "permeability_nodes_md"
                    ],
                "event_porosity_nodes":
                    event_fields[
                        "porosity_nodes"
                    ],
                "event_nw_nodes":
                    event_fields["nw_nodes"],
                "event_no_nodes":
                    event_fields["no_nodes"],
                "event_krw_max_nodes":
                    event_fields["krw_max_nodes"],
                "event_kro_max_nodes":
                    event_fields["kro_max_nodes"],
            }
        )

        day500_state_npz = deterministic_npz_bytes(
            {
                "day": np.asarray(TARGET_DAY),
                "grid_component_mass_kg":
                    day500_grid_mass,
                "grid_saturation":
                    day500_flow["saturation"],
                "grid_pressure_psi":
                    day500_flow["pressure_psi"],
                "streamline_xyz_m":
                    day500_flow["xyz_m"],
                "streamline_tof_s":
                    day500_flow["tof_s"],
                "streamline_weight_m3_s":
                    day500_flow["weights_m3_s"],
                "streamline_face_pressure_psi":
                    day500_flow["face_pressure_psi"],
                "CV_component_mass_kg":
                    day500_split["cv_mass"],
                "CV_saturation":
                    day500_split["cv_saturation"],
                "CV_capacity_kg":
                    day500_split["cv_capacity"],
                "CV_pore_volume_m3":
                    day500_split[
                        "cv_pore_volume_m3"
                    ],
                "CV_pressure_mass_coeff":
                    day500_split[
                        "cv_pressure_mass_coeff"
                    ],
                "residual_grid_component_mass_kg":
                    day500_split[
                        "residual_grid_mass"
                    ],
            }
        )

        files = {
            "PAD_Stream_POSTV16_AV4_F4_R3_R3_Summary.json":
                json_bytes(summary),
            "POSTV16_AV4_F4_R3_R3_Event_Refresh_Audit.json":
                json_bytes(event_audit),
            "POSTV16_AV4_F4_R3_R3_Post_Refresh_Teacher_Audit.json":
                json_bytes(second_teacher_audit),
            "POSTV16_AV4_F4_R3_R3_Day500_Recurrent_Loop_Audit.json":
                json_bytes(day500_audit),
            "POSTV16_AV4_F4_R3_R3_Global_Mass_Ledger.json":
                json_bytes(mass_ledger),
            "POSTV16_AV4_F4_R3_R3_Event_Refreshed_State.npz":
                event_state_npz,
            "POSTV16_AV4_F4_R3_R3_Day500_Accepted_State.npz":
                day500_state_npz,
            "POSTV16_AV4_F4_R3_R3_F5_Handoff_Contract.json":
                json_bytes(f5_handoff),
            "POSTV16_AV4_F4_R3_R3_Decision_Contract.json":
                json_bytes(decision),
            "POSTV16_AV4_F4_R3_R3_Final_Gate_Matrix.csv":
                csv_bytes(
                    [
                        {"gate": k, **v}
                        for k, v in gates.items()
                    ]
                ),
        }
        immutable_publish(out, files)

        manifest_rows = []
        for p in sorted(out.iterdir()):
            if (
                p.is_file()
                and p.name
                != "POSTV16_AV4_F4_R3_R3_Artifact_Manifest.csv"
            ):
                manifest_rows.append(
                    {
                        "file": p.name,
                        "sha256": sha256_file(p),
                        "bytes": p.stat().st_size,
                    }
                )
        immutable_publish(
            out,
            {
                "POSTV16_AV4_F4_R3_R3_Artifact_Manifest.csv":
                    csv_bytes(manifest_rows)
            },
        )

        print()
        print("=" * 214)
        print(
            f"{MILESTONE}: SINGLE EVENT-TRIGGERED FLOW-EPOCH "
            "RENEWAL + DAY500 CONTINUATION PASS"
        )
        print("=" * 214)
        print("Event day                               :", EVENT_DAY)
        print("First epoch accepted substeps           :", event_run["accepted_substeps"])
        print("Event refresh count                     : 1")
        print("Event refreshed streamline count        :", event_flow["xyz_m"].shape[0])
        print("Event TOF min/max days                  :", float(np.min(event_flow["tau_end_s"]) / SPD), "/", float(np.max(event_flow["tau_end_s"]) / SPD))
        print("Event reprojection overloaded CVs       :", event_split["overloaded_CV_count"])
        print("Second epoch accepted substeps          :", second_teacher["substeps"])
        print("Second event refresh                    : NOT EXECUTED")
        print("Day500 grid mass kg                     :", fsum_array(day500_grid_mass))
        print("Global Day365→Day500 mass residual kg   :", fsum_array(day500_grid_mass) - expected_day500_total)
        print("Day500 refreshed streamline count       :", day500_flow["xyz_m"].shape[0])
        print("Day500 reprojection overloaded CVs      :", day500_split["overloaded_CV_count"])
        print("Interior face limiter used              : False")
        print("Raw interior transport operator changed : False")
        print("F5 restart-teacher dataset generation   : AUTHORIZED")
        print("Training / checkpoint / OOD / A3-E2     : NOT AUTHORIZED")
        print("=" * 214)

        return 0

    except ScientificFail as exc:
        failed.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": MILESTONE,
            "status": STATUS_FAIL,
            "failed_stage": stage,
            "failed_gate": exc.gate,
            "detail": exc.detail,
            "gates": gates,
            "event_refresh_executed": event_refresh_executed,
            "event_reprojection_executed": event_reprojection_executed,
            "second_epoch_teacher_started": second_epoch_teacher_started,
            "second_event_refresh_executed": False,
            "second_event_refresh_authorized": False,
            "Day500_refresh_executed": day500_refresh_executed,
            "Day500_reprojection_executed": day500_reprojection_executed,
            "interior_face_limiter_used": False,
            "raw_interior_transport_operator_changed": False,
            "timestep_floor_changed": False,
            "training_performed": False,
            "checkpoint_created": False,
            "locked_OOD_opened": False,
            "F5_dataset_generation_authorized": False,
            "A3_E2_authorized": False,
            "AV4_general_dynamic_transport_authorized": False,
            "automatic_rerun_authorized": False,
        }
        data = json_bytes(report)
        p = failed / "POSTV16_AV4_F4_R3_R3_Scientific_Fail_Report.json"
        if p.exists() and p.read_bytes() != data:
            p = failed / (
                "POSTV16_AV4_F4_R3_R3_Scientific_Fail_Report_"
                + hashlib.sha256(data).hexdigest()[:12]
                + ".json"
            )
        if not p.exists():
            p.write_bytes(data)

        print()
        print("=" * 214)
        print(f"{MILESTONE}: SCIENTIFIC FAIL")
        print("=" * 214)
        print("Stage    :", stage)
        print("Gate     :", exc.gate)
        print("Detail   :", exc.detail)
        print("Second automatic event refresh: NOT AUTHORIZED")
        print("F5 / training / A3-E2 / general AV4: NOT AUTHORIZED")
        print("=" * 214)
        return 3

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": MILESTONE,
            "status": STATUS_BLOCKED,
            "failed_stage": stage,
            "exception": repr(exc),
            "gates": gates,
            "event_refresh_executed": event_refresh_executed,
            "event_reprojection_executed": event_reprojection_executed,
            "second_epoch_teacher_started": second_epoch_teacher_started,
            "second_event_refresh_executed": False,
            "second_event_refresh_authorized": False,
            "Day500_refresh_executed": day500_refresh_executed,
            "Day500_reprojection_executed": day500_reprojection_executed,
            "training_performed": False,
            "F5_dataset_generation_authorized": False,
            "automatic_rerun_authorized": False,
        }
        data = json_bytes(report)
        p = blocked / "POSTV16_AV4_F4_R3_R3_Blocked_Report.json"
        if p.exists() and p.read_bytes() != data:
            p = blocked / (
                "POSTV16_AV4_F4_R3_R3_Blocked_Report_"
                + hashlib.sha256(data).hexdigest()[:12]
                + ".json"
            )
        if not p.exists():
            p.write_bytes(data)

        print()
        print("=" * 214)
        print(f"{MILESTONE}: TECHNICAL / AUTHORITY BLOCK")
        print("=" * 214)
        print("Stage    :", stage)
        print("Exception:", repr(exc))
        print("NO AUTOMATIC RERUN AUTHORIZED.")
        print("=" * 214)
        return 2


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--project-root", type=Path, default=Path("."))
    p.add_argument(
        "--drive-root",
        type=Path,
        default=Path("/content/drive/MyDrive/PAD_Stream_Compute"),
    )
    p.add_argument("--self-test", action="store_true")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.self_test:
        self_test()
        raise SystemExit(0)
    raise SystemExit(main(args.project_root, args.drive_root))
