from __future__ import annotations

from pathlib import Path
import argparse
import csv
import hashlib
import importlib.util
import io
import json
import subprocess
import sys
import zipfile
from collections import defaultdict
from typing import Any

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import lil_matrix, csr_matrix
from scipy.sparse.linalg import spsolve


MILESTONE = "V16E-41-R3-R2"
STATUS = "SATURATION_UPDATED_FLOW_STREAMLINE_CAPACITY_FEASIBILITY_AUDITED"
NEXT = (
    "V16E-41-R3-R3 - Runtime Architecture Repair Selection "
    "(based on R3-R2 flow/support diagnosis)"
)

EXPECTED_GRID = (15, 50, 50)
EXPECTED_CELLS = 37500
LIMITER_CELL = (8, 25, 24)

EXPECTED_R3R1_STATUS = "R3_ACCEPTED_TRANSITION_BUDGET_CAPACITY_REGIME_AUDITED"
EXPECTED_R3R1_PARTIAL_STATE_SHA256 = (
    "8714f5b35b99472de0251def022043076f85fb9cee2ada1cfc4d7b7441cce5e6"
)
EXPECTED_R3R1_PARTIAL_STEP = 3975
EXPECTED_R3R1_PARTIAL_TIME_DAYS = 69.88346704782309

R3R1_REL = Path(
    "provenance/hybrid_dp/"
    "V16E41R3R1_ACCEPTED_TRANSITION_BUDGET_CAPACITY_REGIME_AUDIT"
)
R3R1_SUMMARY = "PAD_Stream_V16E41R3R1_Summary.json"
R3R1_CLOSURE = "V16E41R3R1_Final_Closure.json"
R3R1_STATE = (
    "V16E41R3R1_Diagnostic_Partial_Runtime_State_After_2500_Accepted_"
    "Transitions.npz"
)

E36_REL = Path(
    "provenance/hybrid_dp/"
    "V16E36_SHORT_ADAPTIVE_SGSIM_ROLLOUT_EARLY_PLUME_VALIDATION"
)
E36_CACHE = "V16E36_Certified_Physics_Cache.npz"

OUT_REL = Path(
    "provenance/hybrid_dp/"
    "V16E41R3R2_SATURATION_UPDATED_FLOW_STREAMLINE_CAPACITY_FEASIBILITY_AUDIT"
)
BLOCKED_REL = Path(
    "provenance/hybrid_dp/"
    "V16E41R3R2_BLOCKED_SATURATION_UPDATED_FLOW_STREAMLINE_CAPACITY_FEASIBILITY_AUDIT"
)

# Exact Git blob identities on GitHub main at R3-R2 design freeze.
SOURCE_BLOBS = {
    "SG2": (
        "PAD_Stream_V15SG2_Anisotropic_Transmissibility.py",
        "7242012d3e758472abc3ee7f543831b92d2cf419",
    ),
    "SG3": (
        "PAD_Stream_V15SG3_FiveSpot_Pressure_Solve.py",
        "66a379cd97ee9120f69e7e7e949171541e4918c3",
    ),
    "SG4": (
        "PAD_Stream_V15SG4_Conservative_Darcy_Fluxes.py",
        "8d49f88bdf55b0da087af2bed04e69967740e695",
    ),
    "SG5": (
        "PAD_Stream_V15SG5_Exact_Pollock_Streamlines.py",
        "9a0b64ea7e669904d0d9855ade1c6b052f05ecea",
    ),
    "SG6": (
        "PAD_Stream_V15SG6_TOF_Transport_Coordinates.py",
        "70ceda68e02894167958d753d88b4dbd694731ab",
    ),
    "SG7A": (
        "PAD_Stream_V15SG7A_Full_Physics_TOF_Transport.py",
        "a4dd47338e7a85f130a6a70d0a41211e38c655f8",
    ),
    "SG7D": (
        "PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py",
        "890088c0c0fcab415a2c7351c5079ca8ee12bf82",
    ),
    "R2_PHYSICS": (
        "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_"
        "First_Controlled_Transition.py",
        "a127f8730a16e150713420ea547a8de6255550ef",
    ),
    "E36": (
        "PAD_Stream_V16E36_Short_Adaptive_SGSim_Rollout_and_Early_Plume_"
        "Snapshot_Validation.py",
        "9ab4035c95a25bd61c649f86c82d88f059cef9e2",
    ),
    "E37A": (
        "PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_"
        "Streamline_Grid_Transfer.py",
        "0bbf98ed89cee9128ef1d313c321f9a401b4e9f0",
    ),
    "R3R1": (
        "PAD_Stream_V16E41R3R1_Accepted_Transition_Budget_Capacity_Limited_"
        "Regime_Audit.py",
        "4c3438443513bd527b87e02a766634f5eebd2781",
    ),
    "PERM": (
        "SGSIM_50x50x15_PERM_MD.csv",
        "317dd47d458bc6f880c2e3dc4ec1f69eeb0dd314",
    ),
}

BACKGROUND_SATURATION = 0.20
MAX_INCREMENTAL_CO2_SATURATION = 0.60
INJECTED_BOUNDARY_SATURATION = 0.80
KR_INJECTED_ENDPOINT = 0.80
KR_RESIDENT_ENDPOINT = 0.80
MU_INJECTED_PA_S = 0.50e-3
MU_RESIDENT_PA_S = 5.00e-3
FACE_MOBILITY_RULE = "HARMONIC_TOTAL_MOBILITY"
GRAVITY_DENSITY_POLICY = (
    "SG3_REFERENCE_BRINE_DENSITY_HELD_FIXED_TO_ISOLATE_MOBILITY_FEEDBACK"
)

DAY_TO_S = 86400.0
FT_TO_M = 0.3048

FLOW_LOCAL_REL_TOL = 1.0e-8
FLOW_GLOBAL_REL_TOL = 1.0e-8
STREAMLINE_CAPTURE_TOL = 1.0e-10


class GateError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def json_bytes(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True) + "\n").encode("utf-8")


def csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        return b""
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue().encode("utf-8")


def deterministic_npz_bytes(arrays: dict[str, Any]) -> bytes:
    outer = io.BytesIO()
    with zipfile.ZipFile(
        outer,
        mode="w",
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
        if p.exists():
            if p.read_bytes() != data:
                raise GateError(f"existing_output_differs:{name}")
        else:
            p.write_bytes(data)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_npz(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as z:
        return {k: z[k].copy() for k in z.files}


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError(f"cannot_load_module:{path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def git_blob_sha(path: Path, repo_root: Path) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "hash-object", str(path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


def scalar(a: Any) -> float:
    return float(np.asarray(a).reshape(()))


def int_scalar(a: Any) -> int:
    return int(np.asarray(a).reshape(()))


def phase_mobility_fields(sat: np.ndarray) -> dict[str, np.ndarray]:
    S = np.asarray(sat, dtype=np.float64)
    Se = np.clip(
        (S - BACKGROUND_SATURATION) / MAX_INCREMENTAL_CO2_SATURATION,
        0.0,
        1.0,
    )
    kr_inj = KR_INJECTED_ENDPOINT * Se**2.0
    kr_res = KR_RESIDENT_ENDPOINT * (1.0 - Se) ** 2.0
    lam_inj = kr_inj / MU_INJECTED_PA_S
    lam_res = kr_res / MU_RESIDENT_PA_S
    lam_t = lam_inj + lam_res
    if not np.all(np.isfinite(lam_t)) or np.any(lam_t <= 0.0):
        raise GateError("invalid_total_mobility_field")
    return {
        "effective_injected_saturation": Se,
        "kr_injected": kr_inj,
        "kr_resident": kr_res,
        "lambda_injected": lam_inj,
        "lambda_resident": lam_res,
        "lambda_total": lam_t,
    }


def harmonic_positive(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    denom = a + b
    if np.any(denom <= 0.0):
        raise GateError("nonpositive_harmonic_mobility_denominator")
    return 2.0 * a * b / denom


def build_updated_transmissibilities(
    sg3: Any,
    tx_ref: np.ndarray,
    ty_ref: np.ndarray,
    tz_ref: np.ndarray,
    lambda_total: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, np.ndarray]]:
    lambda_ref = 1.0 / float(sg3.MU_REF_PA_S)

    lam_x = harmonic_positive(
        lambda_total[:, :, :-1],
        lambda_total[:, :, 1:],
    )
    lam_y = harmonic_positive(
        lambda_total[:, :-1, :],
        lambda_total[:, 1:, :],
    )
    lam_z = harmonic_positive(
        lambda_total[:-1, :, :],
        lambda_total[1:, :, :],
    )

    return (
        tx_ref * (lam_x / lambda_ref),
        ty_ref * (lam_y / lambda_ref),
        tz_ref * (lam_z / lambda_ref),
        {
            "lambda_ref": np.asarray(lambda_ref),
            "lambda_x": lam_x,
            "lambda_y": lam_y,
            "lambda_z": lam_z,
        },
    )


def assemble_updated_pressure_system(
    sg3: Any,
    k_cell_md: np.ndarray,
    tx: np.ndarray,
    ty: np.ndarray,
    tz: np.ndarray,
    lambda_total: np.ndarray,
) -> tuple[csr_matrix, np.ndarray, dict[str, list[dict[str, float]]]]:
    A = lil_matrix((sg3.N_CELLS, sg3.N_CELLS), dtype=np.float64)
    b = np.zeros(sg3.N_CELLS, dtype=np.float64)
    lambda_ref = 1.0 / float(sg3.MU_REF_PA_S)
    producer_wi: dict[str, list[dict[str, float]]] = {}

    for k in range(sg3.NZ):
        zc = sg3.cell_center_z_m(k)
        for j in range(sg3.NY):
            for i in range(sg3.NX):
                c = sg3.cell_id(k, j, i)
                diag = 0.0
                rhs_gravity = 0.0

                if i > 0:
                    n = sg3.cell_id(k, j, i - 1)
                    t = tx[k, j, i - 1]
                    diag += t
                    A[c, n] -= t
                if i < sg3.NX - 1:
                    n = sg3.cell_id(k, j, i + 1)
                    t = tx[k, j, i]
                    diag += t
                    A[c, n] -= t
                if j > 0:
                    n = sg3.cell_id(k, j - 1, i)
                    t = ty[k, j - 1, i]
                    diag += t
                    A[c, n] -= t
                if j < sg3.NY - 1:
                    n = sg3.cell_id(k, j + 1, i)
                    t = ty[k, j, i]
                    diag += t
                    A[c, n] -= t
                if k > 0:
                    n = sg3.cell_id(k - 1, j, i)
                    t = tz[k - 1, j, i]
                    zn = sg3.cell_center_z_m(k - 1)
                    diag += t
                    A[c, n] -= t
                    if sg3.GRAVITY_ON:
                        rhs_gravity += (
                            t
                            * sg3.RHO_BRINE_KG_M3
                            * sg3.G_M_S2
                            * (zn - zc)
                        )
                if k < sg3.NZ - 1:
                    n = sg3.cell_id(k + 1, j, i)
                    t = tz[k, j, i]
                    zn = sg3.cell_center_z_m(k + 1)
                    diag += t
                    A[c, n] -= t
                    if sg3.GRAVITY_ON:
                        rhs_gravity += (
                            t
                            * sg3.RHO_BRINE_KG_M3
                            * sg3.G_M_S2
                            * (zn - zc)
                        )

                A[c, c] += diag
                b[c] += rhs_gravity

    for k in sg3.COMPLETION_K:
        c = sg3.cell_id(k, sg3.INJECTOR_J, sg3.INJECTOR_I)
        b[c] += sg3.Q_INJ_PERF_M3_S

    for name, well in sg3.PRODUCERS.items():
        perf_data: list[dict[str, float]] = []
        i = well["i"]
        j = well["j"]

        for k in sg3.COMPLETION_K:
            k_md = float(k_cell_md[k, j, i])
            wi_ref, re = sg3.peaceman_well_index_si(k_md, k_md)
            wi = float(wi_ref) * float(lambda_total[k, j, i] / lambda_ref)

            c = sg3.cell_id(k, j, i)
            A[c, c] += wi
            b[c] += wi * sg3.PRODUCER_BHP_PA

            perf_data.append(
                {
                    "k": int(k),
                    "wi_si": float(wi),
                    "wi_reference_si": float(wi_ref),
                    "mobility_scale": float(lambda_total[k, j, i] / lambda_ref),
                    "re_m": float(re),
                }
            )
        producer_wi[name] = perf_data

    return csr_matrix(A), b, producer_wi


def solve_updated_pressure(
    sg3: Any,
    A: csr_matrix,
    b: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, float]:
    p_pa = np.asarray(spsolve(A, b), dtype=np.float64)
    if not np.all(np.isfinite(p_pa)):
        raise GateError("updated_pressure_nonfinite")
    residual = np.asarray(A @ p_pa - b, dtype=np.float64)
    relative = float(
        np.linalg.norm(residual)
        / max(float(np.linalg.norm(b)), 1.0e-30)
    )
    p_psi = (
        p_pa * sg3.PA_TO_PSI
    ).reshape(EXPECTED_GRID, order="C")
    return p_pa, p_psi, relative


def producer_rates_updated(
    sg3: Any,
    p_psi: np.ndarray,
    producer_wi: dict[str, list[dict[str, float]]],
) -> tuple[dict[str, Any], np.ndarray]:
    rates: dict[str, Any] = {}
    sink = np.zeros(EXPECTED_GRID, dtype=np.float64)

    for name, well in sg3.PRODUCERS.items():
        i = well["i"]
        j = well["j"]
        q_total = 0.0
        perf = []
        for item in producer_wi[name]:
            k = int(item["k"])
            wi = float(item["wi_si"])
            pcell_pa = float(p_psi[k, j, i]) * sg3.PSI_TO_PA
            q = wi * (pcell_pa - sg3.PRODUCER_BHP_PA)
            q_total += q
            sink[k, j, i] += q
            perf.append(float(q * sg3.DAY_TO_S))
        rates[name] = {
            "m3_s": float(q_total),
            "m3_day": float(q_total * sg3.DAY_TO_S),
            "perf_m3_day": perf,
        }
    return rates, sink


def flow_conservation_metrics(
    sg3: Any,
    sg4: Any,
    qx: np.ndarray,
    qy: np.ndarray,
    qz: np.ndarray,
    producer_sink: np.ndarray,
) -> dict[str, float]:
    div = np.asarray(sg4.compute_flux_divergence(qx, qy, qz), dtype=np.float64)
    expected = np.asarray(producer_sink, dtype=np.float64).copy()
    for k in sg3.COMPLETION_K:
        expected[k, sg3.INJECTOR_J, sg3.INJECTOR_I] -= sg3.Q_INJ_PERF_M3_S

    local_residual = div - expected
    local_rel = float(
        np.linalg.norm(local_residual.ravel())
        / max(float(np.linalg.norm(expected.ravel())), 1.0e-30)
    )
    inj = float(sg3.Q_INJ_M3_S)
    prod = float(np.sum(producer_sink))
    global_rel = abs(prod - inj) / max(abs(inj), 1.0e-30)
    return {
        "local_relative_l2_error": local_rel,
        "global_relative_mismatch": float(global_rel),
        "injection_m3_day": float(inj * DAY_TO_S),
        "production_m3_day": float(prod * DAY_TO_S),
        "global_rate_mismatch_m3_day": float((prod - inj) * DAY_TO_S),
    }


def cell_flux_metrics(
    qx: np.ndarray,
    qy: np.ndarray,
    qz: np.ndarray,
    cell: tuple[int, int, int],
    total_injection_m3_s: float,
) -> dict[str, float]:
    k, j, i = cell
    face = {
        "W": float(qx[k, j, i - 1]) if i > 0 else 0.0,
        "E": float(qx[k, j, i]) if i < qx.shape[2] else 0.0,
        "S": float(qy[k, j - 1, i]) if j > 0 else 0.0,
        "N": float(qy[k, j, i]) if j < qy.shape[1] else 0.0,
        "B": float(qz[k - 1, j, i]) if k > 0 else 0.0,
        "T": float(qz[k, j, i]) if k < qz.shape[0] else 0.0,
    }

    inflow = (
        max(face["W"], 0.0)
        + max(-face["E"], 0.0)
        + max(face["S"], 0.0)
        + max(-face["N"], 0.0)
        + max(face["B"], 0.0)
        + max(-face["T"], 0.0)
    )
    outflow = (
        max(-face["W"], 0.0)
        + max(face["E"], 0.0)
        + max(-face["S"], 0.0)
        + max(face["N"], 0.0)
        + max(-face["B"], 0.0)
        + max(face["T"], 0.0)
    )
    return {
        **{f"q_{key}_m3_day": val * DAY_TO_S for key, val in face.items()},
        "inflow_m3_day": float(inflow * DAY_TO_S),
        "outflow_m3_day": float(outflow * DAY_TO_S),
        "net_outward_m3_day": float((outflow - inflow) * DAY_TO_S),
        "inflow_fraction_of_total_injection": float(
            inflow / max(total_injection_m3_s, 1.0e-30)
        ),
    }


def convert_sg5_to_sg6_streamlines(streamlines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for idx, s in enumerate(streamlines):
        result.append(
            {
                "id": idx,
                "points_m": np.asarray(s["points_m"], dtype=np.float64),
                "tau_s": np.asarray(s["times_s"], dtype=np.float64),
                "weight_m3_s": float(s["weight_m3_s"]),
                "tau_end_s": float(s["travel_time_s"]),
                "status": str(s["status"]),
                "producer": str(s["producer"]),
            }
        )
    return result


def transport_nominal_dt_days(sg7a: Any, xi_faces: np.ndarray, tau_end_s: np.ndarray) -> float:
    xi = np.asarray(xi_faces, dtype=np.float64)
    if len(xi) < 2:
        raise GateError("invalid_xi_for_nominal_dt")
    dxi = float(xi[1] - xi[0])
    scan = np.linspace(float(sg7a.S_INITIAL), float(sg7a.S_INJECTED), 4001)
    max_df = float(np.max(np.abs(np.asarray(sg7a.df_dS(scan), dtype=np.float64))))
    u_face = np.asarray(sg7a.u_dimensionless(xi), dtype=np.float64)
    max_wave_speed = float(np.max(u_face) * max_df)
    dtD = float(sg7a.CFL * dxi / (max_wave_speed + sg7a.EPS))
    fastest_tau_days = float(np.min(np.asarray(tau_end_s, dtype=np.float64)) / DAY_TO_S)
    return float(dtD * fastest_tau_days)


def raw_nominal_mapback_audit(
    *,
    r2: Any,
    e36: Any,
    e37a: Any,
    sg7a: Any,
    sg7d: Any,
    parent_saturation: np.ndarray,
    pressure_psi: np.ndarray,
    p_ref_gas_pa: float,
    xyz_m: np.ndarray,
    tau_s: np.ndarray,
    weights_m3_s: np.ndarray,
    xi_faces: np.ndarray,
    cell_pore_volume_m3: float,
    label: str,
) -> dict[str, Any]:
    weights_m3_day = np.asarray(weights_m3_s, dtype=np.float64) * DAY_TO_S
    tof_days = np.asarray(tau_s, dtype=np.float64) / DAY_TO_S
    nstream = int(xyz_m.shape[0])
    nfaces = int(xi_faces.shape[0])
    ncv = nfaces - 1

    operator = sg7d.build_subsegment_operator(
        np.asarray(xyz_m, dtype=np.float64),
        tof_days,
        weights_m3_day,
    )
    geometry = e37a.build_control_volume_geometry(
        r2,
        operator,
        pressure_psi,
        p_ref_gas_pa,
        nstream,
        ncv,
    )
    old_sat, old_mass, sampling_close = e37a.sample_grid_inventory_to_control_volumes(
        r2,
        parent_saturation,
        pressure_psi,
        p_ref_gas_pa,
        geometry,
        nstream,
        ncv,
    )
    face_pressure = e37a.build_face_pressure(
        e36,
        sg7d,
        np.asarray(xyz_m, dtype=np.float64),
        pressure_psi,
    )
    dt_days = transport_nominal_dt_days(
        sg7a,
        np.asarray(xi_faces, dtype=np.float64),
        np.asarray(tau_s[:, -1], dtype=np.float64),
    )
    transport = e37a.advance_component_mass_control_volumes(
        r2,
        sg7a,
        old_sat,
        old_mass,
        geometry["cv_pressure_mass_coeff"],
        face_pressure,
        p_ref_gas_pa,
        weights_m3_day,
        np.asarray(xi_faces, dtype=np.float64),
        dt_days,
    )

    cv_id = np.asarray(geometry["cv_id"], dtype=np.int64)
    flat = np.asarray(geometry["flat_cell"], dtype=np.int64)
    pv = np.asarray(geometry["pv_m3"], dtype=np.float64)
    pseg = np.asarray(geometry["pseg_psi"], dtype=np.float64)

    old_flat = np.asarray(old_sat, dtype=np.float64).reshape(-1)
    new_flat = np.asarray(transport["new_saturation"], dtype=np.float64).reshape(-1)
    old_sub_sat = old_flat[cv_id]
    new_sub_sat = new_flat[cv_id]
    old_sub_sg = np.clip(
        old_sub_sat - BACKGROUND_SATURATION,
        0.0,
        MAX_INCREMENTAL_CO2_SATURATION,
    )
    new_sub_sg = np.clip(
        new_sub_sat - BACKGROUND_SATURATION,
        0.0,
        MAX_INCREMENTAL_CO2_SATURATION,
    )
    rho_old = np.asarray(
        r2.gas_density_from_state(old_sub_sat, pseg, p_ref_gas_pa),
        dtype=np.float64,
    )
    rho_new = np.asarray(
        r2.gas_density_from_state(new_sub_sat, pseg, p_ref_gas_pa),
        dtype=np.float64,
    )
    sub_delta = pv * (rho_new * new_sub_sg - rho_old * old_sub_sg)

    deposited = np.bincount(
        flat,
        weights=sub_delta,
        minlength=EXPECTED_CELLS,
    ).reshape(EXPECTED_GRID)

    parent_sat = np.asarray(parent_saturation, dtype=np.float64)
    parent_sg = np.clip(
        parent_sat - BACKGROUND_SATURATION,
        0.0,
        MAX_INCREMENTAL_CO2_SATURATION,
    )
    parent_rho = np.asarray(
        r2.gas_density_from_state(parent_sat, pressure_psi, p_ref_gas_pa),
        dtype=np.float64,
    )
    parent_mass = float(cell_pore_volume_m3) * parent_rho * parent_sg

    smax = np.full(EXPECTED_GRID, INJECTED_BOUNDARY_SATURATION, dtype=np.float64)
    rho_max = np.asarray(
        r2.gas_density_from_state(smax, pressure_psi, p_ref_gas_pa),
        dtype=np.float64,
    )
    capacity = (
        float(cell_pore_volume_m3)
        * rho_max
        * MAX_INCREMENTAL_CO2_SATURATION
    )
    trial_mass = parent_mass + deposited

    capacity_tol = max(
        1.0e-8,
        1.0e-12 * max(float(np.max(capacity)), 1.0),
    )
    excess = trial_mass - capacity
    over_mask = excess > capacity_tol
    over_flat = np.flatnonzero(over_mask.ravel())

    cv_delta = float(
        np.sum(np.asarray(transport["new_mass"], dtype=np.float64))
        - np.sum(np.asarray(old_mass, dtype=np.float64))
    )
    sub_delta_total = float(np.sum(sub_delta))
    transfer_residual = sub_delta_total - cv_delta

    return {
        "label": label,
        "operator": operator,
        "geometry": geometry,
        "old_cv_saturation": old_sat,
        "old_cv_mass": old_mass,
        "new_cv_saturation": transport["new_saturation"],
        "new_cv_mass": transport["new_mass"],
        "sub_delta_mass": sub_delta,
        "deposited_delta_mass": deposited,
        "parent_mass": parent_mass,
        "capacity_mass": capacity,
        "trial_mass": trial_mass,
        "capacity_excess": excess,
        "overcapacity_flat_cells": over_flat,
        "capacity_tolerance_kg": float(capacity_tol),
        "nominal_dt_days": float(dt_days),
        "sampling_closure_kg": float(sampling_close),
        "transport_mass_residual_kg": float(transport["mass_residual_kg"]),
        "CV_to_subsegment_transfer_residual_kg": float(transfer_residual),
        "CV_delta_mass_kg": float(cv_delta),
        "subsegment_delta_mass_kg": float(sub_delta_total),
        "injected_mass_kg": float(transport["injected_mass_kg"]),
        "produced_mass_kg": float(transport["produced_mass_kg"]),
    }


def local_excess_reroute_feasibility(
    raw: dict[str, Any],
) -> dict[str, Any]:
    operator = raw["operator"]
    geometry = raw["geometry"]
    flat = np.asarray(geometry["flat_cell"], dtype=np.int64)
    cv_id = np.asarray(geometry["cv_id"], dtype=np.int64)
    sub_delta = np.asarray(raw["sub_delta_mass"], dtype=np.float64)
    trial_mass = np.asarray(raw["trial_mass"], dtype=np.float64).ravel()
    capacity = np.asarray(raw["capacity_mass"], dtype=np.float64).ravel()
    over_flat = np.asarray(raw["overcapacity_flat_cells"], dtype=np.int64)
    tol = float(raw["capacity_tolerance_kg"])

    if len(over_flat) == 0:
        return {
            "status": "NO_RAW_OVERCAPACITY",
            "feasible": True,
            "required_excess_mass_kg": 0.0,
            "minimum_rerouted_mass_kg": 0.0,
            "affected_overcapacity_cells": 0,
            "affected_source_units": 0,
            "candidate_destination_cells": 0,
            "LP_status": "NOT_REQUIRED",
            "moves": [],
        }

    edge_delta: dict[tuple[int, int], float] = defaultdict(float)
    support_by_cv: dict[int, set[int]] = defaultdict(set)

    for cvid, cell, dm in zip(cv_id.tolist(), flat.tolist(), sub_delta.tolist()):
        edge_delta[(int(cvid), int(cell))] += float(dm)
        support_by_cv[int(cvid)].add(int(cell))

    over_set = set(int(x) for x in over_flat.tolist())
    excess_required = {
        int(cell): float(trial_mass[cell] - capacity[cell])
        for cell in over_flat
    }

    sources: list[dict[str, Any]] = []
    for cell in over_flat:
        f = int(cell)
        for (cvid, edge_cell), dm in edge_delta.items():
            if edge_cell == f and dm > tol:
                sources.append(
                    {
                        "cv_id": int(cvid),
                        "over_cell": f,
                        "movable_mass_kg": float(dm),
                    }
                )

    headroom = np.maximum(capacity - trial_mass, 0.0)
    destination_cells = sorted(
        {
            dest
            for src in sources
            for dest in support_by_cv[src["cv_id"]]
            if dest not in over_set and headroom[dest] > tol
        }
    )

    variable_edges: list[tuple[int, int]] = []
    for sidx, src in enumerate(sources):
        for dest in sorted(support_by_cv[src["cv_id"]]):
            if dest in over_set:
                continue
            if headroom[dest] <= tol:
                continue
            variable_edges.append((sidx, int(dest)))

    required_total = float(sum(excess_required.values()))
    if not variable_edges:
        return {
            "status": "NO_ADMISSIBLE_DESTINATION_EDGES",
            "feasible": False,
            "required_excess_mass_kg": required_total,
            "minimum_rerouted_mass_kg": None,
            "affected_overcapacity_cells": len(over_flat),
            "affected_source_units": len(sources),
            "candidate_destination_cells": len(destination_cells),
            "LP_status": "NO_VARIABLES",
            "moves": [],
        }

    nvar = len(variable_edges)
    rows = []
    rhs = []

    # Source contribution cannot be moved more than its raw contribution
    # to the overfull cell.
    for sidx, src in enumerate(sources):
        row = np.zeros(nvar, dtype=np.float64)
        for vidx, (edge_sidx, _dest) in enumerate(variable_edges):
            if edge_sidx == sidx:
                row[vidx] = 1.0
        rows.append(row)
        rhs.append(float(src["movable_mass_kg"]))

    # Destination headroom cannot be exceeded.
    for dest in destination_cells:
        row = np.zeros(nvar, dtype=np.float64)
        for vidx, (_sidx, edge_dest) in enumerate(variable_edges):
            if edge_dest == dest:
                row[vidx] = 1.0
        rows.append(row)
        rhs.append(float(headroom[dest]))

    # Each overfull cell must shed at least its own excess.
    for over_cell, required in excess_required.items():
        row = np.zeros(nvar, dtype=np.float64)
        for vidx, (sidx, _dest) in enumerate(variable_edges):
            if sources[sidx]["over_cell"] == over_cell:
                row[vidx] = -1.0
        rows.append(row)
        rhs.append(-float(required))

    A_ub = np.asarray(rows, dtype=np.float64)
    b_ub = np.asarray(rhs, dtype=np.float64)
    c = np.ones(nvar, dtype=np.float64)

    result = linprog(
        c,
        A_ub=A_ub,
        b_ub=b_ub,
        bounds=[(0.0, None)] * nvar,
        method="highs",
    )

    moves: list[dict[str, Any]] = []
    if result.success:
        for value, (sidx, dest) in zip(result.x.tolist(), variable_edges):
            if value <= max(tol, 1.0e-12):
                continue
            src = sources[sidx]
            moves.append(
                {
                    "cv_id": int(src["cv_id"]),
                    "from_overfull_flat_cell": int(src["over_cell"]),
                    "to_flat_cell": int(dest),
                    "rerouted_mass_kg": float(value),
                }
            )

    moved = float(np.sum(result.x)) if result.success else None

    return {
        "status": "FEASIBLE" if result.success else "INFEASIBLE",
        "feasible": bool(result.success),
        "required_excess_mass_kg": required_total,
        "minimum_rerouted_mass_kg": moved,
        "affected_overcapacity_cells": len(over_flat),
        "affected_source_units": len(sources),
        "candidate_destination_cells": len(destination_cells),
        "LP_status": str(result.message),
        "LP_fun": float(result.fun) if result.success else None,
        "moves": moves,
    }


def support_metrics_for_cell(
    operator: dict[str, np.ndarray],
    cell: tuple[int, int, int],
) -> dict[str, Any]:
    k, j, i = cell
    mask = (
        (np.asarray(operator["k"]) == k)
        & (np.asarray(operator["j"]) == j)
        & (np.asarray(operator["i"]) == i)
    )
    streamlines = np.unique(np.asarray(operator["streamline"])[mask])
    cv_ids = np.unique(
        np.asarray(operator["streamline"])[mask].astype(np.int64) * 200
        + np.asarray(operator["node"])[mask].astype(np.int64)
    )
    return {
        "subsegment_count": int(np.sum(mask)),
        "unique_streamline_count": int(len(streamlines)),
        "unique_control_volume_count": int(len(cv_ids)),
        "support_pore_volume_m3": float(
            np.sum(np.asarray(operator["pv_m3"], dtype=np.float64)[mask])
        ),
    }


def producer_weight_fractions(
    producer: np.ndarray,
    weights_m3_s: np.ndarray,
) -> dict[str, float]:
    labels = np.asarray(producer).astype(str)
    w = np.asarray(weights_m3_s, dtype=np.float64)
    total = float(np.sum(w))
    out: dict[str, float] = {}
    for name in sorted(set(labels.tolist())):
        mask = labels == name
        out[name] = float(np.sum(w[mask]) / max(total, 1.0e-30))
    return out


def self_test() -> None:
    a = np.asarray([1.0, 2.0])
    b = np.asarray([3.0, 4.0])
    h = harmonic_positive(a, b)
    expected = 2.0 * a * b / (a + b)
    if not np.allclose(h, expected):
        raise RuntimeError("self_test_harmonic")

    # Tiny LP: one overfull-cell source can move 1 kg into a 2 kg headroom.
    c = np.ones(1)
    A = np.asarray([[1.0], [1.0], [-1.0]])
    bb = np.asarray([1.5, 2.0, -1.0])
    r = linprog(c, A_ub=A, b_ub=bb, bounds=[(0.0, None)], method="highs")
    if not r.success or abs(float(r.x[0]) - 1.0) > 1.0e-10:
        raise RuntimeError("self_test_local_LP")

    print(
        "PAD-Stream V16E-41-R3-R2 saturation-updated flow / "
        "streamline-connectivity / capacity-feasibility audit self-test: PASS"
    )


def main(project_root: Path, drive_root: Path) -> int:
    root = Path(project_root).resolve()
    drive = Path(drive_root).resolve()
    out = drive / OUT_REL
    blocked = drive / BLOCKED_REL

    gates: dict[str, dict[str, Any]] = {}
    failed_stage: str | None = None

    def gate(name: str, passed: bool, detail: Any = "") -> None:
        gates[name] = {"passed": bool(passed), "detail": str(detail)}
        if not passed:
            raise GateError(name)

    try:
        print("\n" + "=" * 152)
        print(
            "PAD-Stream V16E-41-R3-R2 — Saturation-Updated Flow / "
            "Streamline Connectivity / Capacity Feasibility Audit"
        )
        print("=" * 152)
        print("ROLE        : diagnostic only")
        print("STATE       : formal R3-R1 partial state at the persistent capacity lock")
        print(
            "FLOW UPDATE : two-phase Corey total mobility; harmonic face mobility; "
            "SG3 finite-volume pressure topology"
        )
        print(
            "GRAVITY     : SG3 reference-brine gravity density held fixed to isolate "
            "saturation-mobility feedback"
        )
        print("STREAMLINES : exact SG5 Pollock retrace + SG6 TOF reconstruction")
        print(
            "SUPPORT TEST: local excess reroute only through exact updated CV/grid "
            "overlap edges; no new support"
        )
        print("REPAIR      : none")
        print("100D CLAIM  : none")

        failed_stage = "source_identity_binding"

        modules: dict[str, Any] = {}
        paths: dict[str, Path] = {}
        for role, (filename, expected_blob) in SOURCE_BLOBS.items():
            p = root / filename
            gate(f"source_exists_{role}", p.is_file(), p)
            actual_blob = git_blob_sha(p, root)
            gate(
                f"source_git_blob_exact_{role}",
                actual_blob == expected_blob,
                actual_blob,
            )
            paths[role] = p

        sg2 = load_module(paths["SG2"], "pad_stream_v16e41r3r2_sg2")
        sg3 = load_module(paths["SG3"], "pad_stream_v16e41r3r2_sg3")
        sg4 = load_module(paths["SG4"], "pad_stream_v16e41r3r2_sg4")
        sg5 = load_module(paths["SG5"], "pad_stream_v16e41r3r2_sg5")
        sg6 = load_module(paths["SG6"], "pad_stream_v16e41r3r2_sg6")
        sg7a = load_module(paths["SG7A"], "pad_stream_v16e41r3r2_sg7a")
        sg7d = load_module(paths["SG7D"], "pad_stream_v16e41r3r2_sg7d")
        r2 = load_module(paths["R2_PHYSICS"], "pad_stream_v16e41r3r2_r2")
        e36 = load_module(paths["E36"], "pad_stream_v16e41r3r2_e36")
        e37a = load_module(paths["E37A"], "pad_stream_v16e41r3r2_e37a")

        failed_stage = "formal_R3R1_state_binding"

        r3r1_dir = drive / R3R1_REL
        summary_path = r3r1_dir / R3R1_SUMMARY
        closure_path = r3r1_dir / R3R1_CLOSURE
        state_path = r3r1_dir / R3R1_STATE
        cache_path = drive / E36_REL / E36_CACHE

        for p in [summary_path, closure_path, state_path, cache_path]:
            gate(f"provenance_exists_{p.name}", p.is_file(), p)

        summary = load_json(summary_path)
        closure = load_json(closure_path)
        state_sha_before = sha256_file(state_path)
        cache_sha_before = sha256_file(cache_path)

        gate(
            "R3R1_status_exact",
            summary.get("status") == EXPECTED_R3R1_STATUS,
            summary.get("status"),
        )
        gate(
            "R3R1_closure_pass",
            closure.get("all_audit_gates_passed") is True,
            closure.get("all_audit_gates_passed"),
        )
        gate(
            "R3R1_partial_state_SHA_exact",
            state_sha_before == EXPECTED_R3R1_PARTIAL_STATE_SHA256,
            state_sha_before,
        )

        state = load_npz(state_path)
        cache = load_npz(cache_path)

        step = int_scalar(state["accepted_step_index"])
        time_days = scalar(state["physical_time_days"])
        gate("R3R1_partial_step_exact", step == EXPECTED_R3R1_PARTIAL_STEP, step)
        gate(
            "R3R1_partial_time_exact",
            abs(time_days - EXPECTED_R3R1_PARTIAL_TIME_DAYS) <= 1.0e-12,
            time_days,
        )
        gate(
            "R3R1_not_100d_canonical",
            not bool(np.asarray(
                state["V16E41_canonical_100d_observation_state"]
            ).reshape(())),
        )

        parent_sat = np.asarray(state["transport_saturation"], dtype=np.float64)
        frozen_pressure = np.asarray(cache["accepted_pressure_psi"], dtype=np.float64)
        frozen_qx = np.asarray(cache["qx_m3_s"], dtype=np.float64)
        frozen_qy = np.asarray(cache["qy_m3_s"], dtype=np.float64)
        frozen_qz = np.asarray(cache["qz_m3_s"], dtype=np.float64)
        old_xyz = np.asarray(cache["streamline_xyz_m"], dtype=np.float64)
        old_tau = np.asarray(cache["streamline_tof_s"], dtype=np.float64)
        old_weights = np.asarray(cache["streamline_weights_m3_s"], dtype=np.float64)
        old_labels = np.asarray(cache["producer_labels"]).astype(str)
        old_xi = np.asarray(cache["xi"], dtype=np.float64)
        p_ref_gas_pa = scalar(state["co2_density_reference_pressure_pa"])

        gate("partial_saturation_shape_exact", parent_sat.shape == EXPECTED_GRID)
        gate("frozen_pressure_shape_exact", frozen_pressure.shape == EXPECTED_GRID)

        failed_stage = "saturation_updated_total_mobility_pressure_solve"

        permeability = np.loadtxt(
            paths["PERM"],
            skiprows=1,
            dtype=np.float64,
        ).reshape(EXPECTED_GRID, order="C")

        kx, ky, kz = sg2.build_directional_permeability(permeability)
        kfx, kfy, kfz = sg2.build_face_permeabilities(kx, ky, kz)
        tx_ref, ty_ref, tz_ref = sg3.construct_si_transmissibilities(kfx, kfy, kfz)

        mobility = phase_mobility_fields(parent_sat)
        tx, ty, tz, face_mobility = build_updated_transmissibilities(
            sg3,
            tx_ref,
            ty_ref,
            tz_ref,
            mobility["lambda_total"],
        )

        A, b, producer_wi = assemble_updated_pressure_system(
            sg3,
            permeability,
            tx,
            ty,
            tz,
            mobility["lambda_total"],
        )
        _p_pa, updated_pressure, pressure_relative_residual = solve_updated_pressure(
            sg3,
            A,
            b,
        )
        gate(
            "updated_pressure_linear_residual",
            pressure_relative_residual < 1.0e-8,
            pressure_relative_residual,
        )

        producer_rates, producer_sink = producer_rates_updated(
            sg3,
            updated_pressure,
            producer_wi,
        )
        gate(
            "updated_BHP_wells_remain_producers",
            all(float(v["m3_s"]) > 0.0 for v in producer_rates.values()),
            {k: float(v["m3_day"]) for k, v in producer_rates.items()},
        )
        updated_qx, updated_qy, updated_qz = sg4.compute_face_fluxes(
            updated_pressure,
            tx,
            ty,
            tz,
        )
        conservation = flow_conservation_metrics(
            sg3,
            sg4,
            updated_qx,
            updated_qy,
            updated_qz,
            producer_sink,
        )
        gate(
            "updated_flow_local_conservation",
            conservation["local_relative_l2_error"] < FLOW_LOCAL_REL_TOL,
            conservation["local_relative_l2_error"],
        )
        gate(
            "updated_flow_global_conservation",
            conservation["global_relative_mismatch"] < FLOW_GLOBAL_REL_TOL,
            conservation["global_relative_mismatch"],
        )

        frozen_cell_flux = cell_flux_metrics(
            frozen_qx,
            frozen_qy,
            frozen_qz,
            LIMITER_CELL,
            float(sg3.Q_INJ_M3_S),
        )
        updated_cell_flux = cell_flux_metrics(
            updated_qx,
            updated_qy,
            updated_qz,
            LIMITER_CELL,
            float(sg3.Q_INJ_M3_S),
        )

        failed_stage = "updated_exact_Pollock_streamline_retrace"

        vx, vy, vz = sg5.construct_face_pore_velocities(
            updated_qx,
            updated_qy,
            updated_qz,
        )
        faces, seeds = sg5.build_seeds(updated_qx, updated_qy, updated_qz)
        streamlines = sg5.trace_streamlines(seeds, vx, vy, vz)

        seed_weight = float(sum(float(s["weight_m3_s"]) for s in seeds))
        captured = [s for s in streamlines if s["status"] == "PRODUCER"]
        captured_weight = float(
            sum(float(s["weight_m3_s"]) for s in captured)
        )
        capture_fraction = captured_weight / max(seed_weight, 1.0e-30)
        outgoing_q = float(sum(float(f["q_m3_s"]) for f in faces))
        inj_q = float(sg3.Q_INJ_M3_S)

        gate(
            "updated_seed_weight_matches_injector_outflow",
            abs(seed_weight - outgoing_q)
            <= 1.0e-10 * max(abs(outgoing_q), 1.0e-30),
            f"{seed_weight}:{outgoing_q}",
        )
        gate(
            "updated_injector_outflow_matches_rate_control",
            abs(outgoing_q - inj_q)
            <= 1.0e-8 * max(abs(inj_q), 1.0e-30),
            f"{outgoing_q}:{inj_q}",
        )
        gate(
            "updated_streamline_full_weight_capture",
            abs(capture_fraction - 1.0) <= STREAMLINE_CAPTURE_TOL,
            capture_fraction,
        )

        sg6_streamlines = convert_sg5_to_sg6_streamlines(streamlines)
        updated_db = sg6.build_transport_database(sg6_streamlines)
        gate(
            "updated_transport_streamline_count_matches_seed_count",
            int(updated_db["xyz_m"].shape[0]) == len(seeds),
            f"{updated_db['xyz_m'].shape[0]}:{len(seeds)}",
        )

        updated_operator = sg7d.build_subsegment_operator(
            np.asarray(updated_db["xyz_m"], dtype=np.float64),
            np.asarray(updated_db["tau_s"], dtype=np.float64) / DAY_TO_S,
            np.asarray(updated_db["weights_m3_s"], dtype=np.float64) * DAY_TO_S,
        )
        old_operator = sg7d.build_subsegment_operator(
            old_xyz,
            old_tau / DAY_TO_S,
            old_weights * DAY_TO_S,
        )

        old_support = support_metrics_for_cell(old_operator, LIMITER_CELL)
        updated_support = support_metrics_for_cell(updated_operator, LIMITER_CELL)

        old_tof_end_days = old_tau[:, -1] / DAY_TO_S
        updated_tof_end_days = (
            np.asarray(updated_db["tau_end_s"], dtype=np.float64) / DAY_TO_S
        )

        old_producer_fraction = producer_weight_fractions(old_labels, old_weights)
        updated_producer_fraction = producer_weight_fractions(
            np.asarray(updated_db["producer"]),
            np.asarray(updated_db["weights_m3_s"]),
        )

        failed_stage = "nominal_transport_raw_mapback_comparison"

        dx_m = 20.0 * FT_TO_M
        dy_m = 20.0 * FT_TO_M
        dz_m = 4.0 * FT_TO_M
        cell_pore_volume_m3 = 0.20 * dx_m * dy_m * dz_m

        old_raw = raw_nominal_mapback_audit(
            r2=r2,
            e36=e36,
            e37a=e37a,
            sg7a=sg7a,
            sg7d=sg7d,
            parent_saturation=parent_sat,
            pressure_psi=frozen_pressure,
            p_ref_gas_pa=p_ref_gas_pa,
            xyz_m=old_xyz,
            tau_s=old_tau,
            weights_m3_s=old_weights,
            xi_faces=old_xi,
            cell_pore_volume_m3=cell_pore_volume_m3,
            label="FROZEN_REFERENCE_FLOW",
        )

        updated_raw = raw_nominal_mapback_audit(
            r2=r2,
            e36=e36,
            e37a=e37a,
            sg7a=sg7a,
            sg7d=sg7d,
            parent_saturation=parent_sat,
            pressure_psi=updated_pressure,
            p_ref_gas_pa=p_ref_gas_pa,
            xyz_m=np.asarray(updated_db["xyz_m"], dtype=np.float64),
            tau_s=np.asarray(updated_db["tau_s"], dtype=np.float64),
            weights_m3_s=np.asarray(updated_db["weights_m3_s"], dtype=np.float64),
            xi_faces=np.asarray(updated_db["xi"], dtype=np.float64),
            cell_pore_volume_m3=cell_pore_volume_m3,
            label="SATURATION_UPDATED_FLOW",
        )

        old_lp = local_excess_reroute_feasibility(old_raw)
        updated_lp = local_excess_reroute_feasibility(updated_raw)

        limiter_flat = (
            (LIMITER_CELL[0] * EXPECTED_GRID[1] + LIMITER_CELL[1])
            * EXPECTED_GRID[2]
            + LIMITER_CELL[2]
        )

        old_limiter_excess = float(
            old_raw["capacity_excess"].ravel()[limiter_flat]
        )
        updated_limiter_excess = float(
            updated_raw["capacity_excess"].ravel()[limiter_flat]
        )

        old_over_count = int(len(old_raw["overcapacity_flat_cells"]))
        updated_over_count = int(len(updated_raw["overcapacity_flat_cells"]))

        failed_stage = "diagnostic_classification_and_closure"

        limiter_inflow_fraction_old = float(
            frozen_cell_flux["inflow_fraction_of_total_injection"]
        )
        limiter_inflow_fraction_updated = float(
            updated_cell_flux["inflow_fraction_of_total_injection"]
        )
        limiter_flux_reduction = (
            1.0
            - limiter_inflow_fraction_updated
            / max(limiter_inflow_fraction_old, 1.0e-30)
        )

        if updated_over_count == 0:
            diagnosis = "UPDATED_FLOW_NATURALLY_REMOVES_MAPBACK_CAPACITY_LOCK"
            repair_direction = (
                "Promote saturation-updated pressure/flux/streamline refresh into "
                "a controlled runtime architecture milestone; no constrained "
                "map-back redistribution is needed for the audited nominal step."
            )
        elif updated_lp["feasible"]:
            diagnosis = (
                "UPDATED_FLOW_STILL_CAPACITY_LIMITED_BUT_EXISTING_UPDATED_"
                "CV_SUPPORT_CAN_REROUTE_EXCESS_CONSERVATIVELY"
            )
            repair_direction = (
                "Design a conservative capacity-constrained map-back that moves "
                "only the overcapacity excess within each exact updated CV/grid "
                "overlap support, preserving CV mass and forbidding new support."
            )
        else:
            diagnosis = (
                "UPDATED_FLOW_SUPPORT_INSUFFICIENT_FOR_LOCAL_CONSERVATIVE_REROUTE"
            )
            repair_direction = (
                "Do not force a map-back projection. Investigate tighter "
                "transport/capillary coupling or more frequent flow refresh, "
                "because updated Darcy/streamline support cannot absorb the "
                "nominal transported excess."
            )

        flow_rows = [
            {
                "metric": "limiter_cell_inflow_m3_day",
                "frozen_reference": frozen_cell_flux["inflow_m3_day"],
                "saturation_updated": updated_cell_flux["inflow_m3_day"],
            },
            {
                "metric": "limiter_cell_outflow_m3_day",
                "frozen_reference": frozen_cell_flux["outflow_m3_day"],
                "saturation_updated": updated_cell_flux["outflow_m3_day"],
            },
            {
                "metric": "limiter_cell_inflow_fraction_of_total_injection",
                "frozen_reference": limiter_inflow_fraction_old,
                "saturation_updated": limiter_inflow_fraction_updated,
            },
            {
                "metric": "limiter_cell_unique_streamline_count",
                "frozen_reference": old_support["unique_streamline_count"],
                "saturation_updated": updated_support["unique_streamline_count"],
            },
            {
                "metric": "limiter_cell_unique_control_volume_count",
                "frozen_reference": old_support["unique_control_volume_count"],
                "saturation_updated": updated_support["unique_control_volume_count"],
            },
            {
                "metric": "limiter_cell_support_pore_volume_m3",
                "frozen_reference": old_support["support_pore_volume_m3"],
                "saturation_updated": updated_support["support_pore_volume_m3"],
            },
            {
                "metric": "TOF_flux_weighted_mean_days",
                "frozen_reference": float(
                    np.sum(old_tof_end_days * old_weights) / np.sum(old_weights)
                ),
                "saturation_updated": float(
                    np.sum(
                        updated_tof_end_days
                        * np.asarray(updated_db["weights_m3_s"], dtype=np.float64)
                    )
                    / np.sum(np.asarray(updated_db["weights_m3_s"], dtype=np.float64))
                ),
            },
            {
                "metric": "nominal_transport_dt_days",
                "frozen_reference": old_raw["nominal_dt_days"],
                "saturation_updated": updated_raw["nominal_dt_days"],
            },
            {
                "metric": "raw_overcapacity_cell_count",
                "frozen_reference": old_over_count,
                "saturation_updated": updated_over_count,
            },
            {
                "metric": "limiter_cell_raw_capacity_excess_kg",
                "frozen_reference": old_limiter_excess,
                "saturation_updated": updated_limiter_excess,
            },
        ]

        producer_rows = []
        producer_names = sorted(
            set(old_producer_fraction) | set(updated_producer_fraction)
        )
        for name in producer_names:
            producer_rows.append(
                {
                    "producer": name,
                    "frozen_weight_fraction": old_producer_fraction.get(name, 0.0),
                    "updated_weight_fraction": updated_producer_fraction.get(name, 0.0),
                    "difference_updated_minus_frozen": (
                        updated_producer_fraction.get(name, 0.0)
                        - old_producer_fraction.get(name, 0.0)
                    ),
                }
            )

        limiter_support_rows = []
        for variant, raw in [("FROZEN", old_raw), ("UPDATED", updated_raw)]:
            op = raw["operator"]
            mask = (
                (np.asarray(op["k"]) == LIMITER_CELL[0])
                & (np.asarray(op["j"]) == LIMITER_CELL[1])
                & (np.asarray(op["i"]) == LIMITER_CELL[2])
            )
            streams = np.asarray(op["streamline"])[mask]
            nodes = np.asarray(op["node"])[mask]
            pv = np.asarray(op["pv_m3"], dtype=np.float64)[mask]
            for s, n, pvv in zip(streams.tolist(), nodes.tolist(), pv.tolist()):
                limiter_support_rows.append(
                    {
                        "variant": variant,
                        "streamline": int(s),
                        "control_volume_node": int(n),
                        "subsegment_pore_volume_m3": float(pvv),
                    }
                )

        old_capacity_summary = {
            "nominal_dt_days": old_raw["nominal_dt_days"],
            "overcapacity_cell_count": old_over_count,
            "max_capacity_excess_kg": float(
                max(np.max(old_raw["capacity_excess"]), 0.0)
            ),
            "limiter_cell_excess_kg": old_limiter_excess,
            "local_support_reroute": {
                k: v for k, v in old_lp.items() if k != "moves"
            },
            "moves": old_lp["moves"],
        }
        updated_capacity_summary = {
            "nominal_dt_days": updated_raw["nominal_dt_days"],
            "overcapacity_cell_count": updated_over_count,
            "max_capacity_excess_kg": float(
                max(np.max(updated_raw["capacity_excess"]), 0.0)
            ),
            "limiter_cell_excess_kg": updated_limiter_excess,
            "local_support_reroute": {
                k: v for k, v in updated_lp.items() if k != "moves"
            },
            "moves": updated_lp["moves"],
        }

        pressure_rel_l2 = float(
            np.linalg.norm((updated_pressure - frozen_pressure).ravel())
            / max(float(np.linalg.norm(frozen_pressure.ravel())), 1.0e-30)
        )

        summary_out = {
            "milestone": MILESTONE,
            "status": STATUS,
            "diagnostic_only": True,
            "solver_repair_performed": False,
            "canonical_100d_state_created": False,
            "legacy_regression_started": False,
            "input_partial_state_step": step,
            "input_partial_state_time_days": time_days,
            "input_partial_state_sha256": state_sha_before,
            "limiter_cell_zero_based": list(LIMITER_CELL),
            "mobility_model": {
                "effective_saturation": "(S-0.20)/0.60 clipped [0,1]",
                "kr_injected": "0.80*Se^2",
                "kr_resident": "0.80*(1-Se)^2",
                "mu_injected_Pa_s": MU_INJECTED_PA_S,
                "mu_resident_Pa_s": MU_RESIDENT_PA_S,
                "face_total_mobility_rule": FACE_MOBILITY_RULE,
                "gravity_density_policy": GRAVITY_DENSITY_POLICY,
            },
            "updated_pressure_relative_linear_residual": pressure_relative_residual,
            "updated_pressure_relative_L2_vs_frozen": pressure_rel_l2,
            "updated_pressure_min_psi": float(np.min(updated_pressure)),
            "updated_pressure_max_psi": float(np.max(updated_pressure)),
            "updated_flow_conservation": conservation,
            "updated_streamline_seed_count": len(seeds),
            "updated_streamline_capture_fraction": capture_fraction,
            "updated_streamline_producer_count": len(captured),
            "limiter_cell_frozen_flow": frozen_cell_flux,
            "limiter_cell_updated_flow": updated_cell_flux,
            "limiter_inflow_fraction_reduction": float(limiter_flux_reduction),
            "limiter_cell_frozen_support": old_support,
            "limiter_cell_updated_support": updated_support,
            "frozen_nominal_capacity_audit": old_capacity_summary,
            "updated_nominal_capacity_audit": updated_capacity_summary,
            "diagnosis": diagnosis,
            "recommended_repair_direction": repair_direction,
            "next_milestone": NEXT,
        }

        closure_out = {
            "milestone": MILESTONE,
            "status": STATUS,
            "all_audit_gates_passed": all(v["passed"] for v in gates.values()),
            "gate_count": len(gates),
            "diagnostic_only": True,
            "solver_repair_performed": False,
            "input_partial_state_unchanged": sha256_file(state_path) == state_sha_before,
            "E36_cache_unchanged": sha256_file(cache_path) == cache_sha_before,
            "canonical_100d_state_created": False,
            "legacy_regression_started": False,
            "diagnosis": diagnosis,
            "next_milestone": NEXT,
        }

        gate(
            "R3R1_partial_state_unchanged",
            sha256_file(state_path) == state_sha_before,
            sha256_file(state_path),
        )
        gate(
            "E36_cache_unchanged",
            sha256_file(cache_path) == cache_sha_before,
            sha256_file(cache_path),
        )
        closure_out["all_audit_gates_passed"] = all(
            v["passed"] for v in gates.values()
        )
        closure_out["gate_count"] = len(gates)

        flow_npz = deterministic_npz_bytes(
            {
                "updated_pressure_psi": updated_pressure,
                "updated_qx_m3_s": updated_qx,
                "updated_qy_m3_s": updated_qy,
                "updated_qz_m3_s": updated_qz,
                "lambda_total_cell_1_Pa_s": mobility["lambda_total"],
                "effective_injected_saturation": mobility[
                    "effective_injected_saturation"
                ],
                "kr_injected": mobility["kr_injected"],
                "kr_resident": mobility["kr_resident"],
            }
        )
        streamline_npz = deterministic_npz_bytes(
            {
                "xyz_m": np.asarray(updated_db["xyz_m"], dtype=np.float64),
                "tau_s": np.asarray(updated_db["tau_s"], dtype=np.float64),
                "weights_m3_s": np.asarray(
                    updated_db["weights_m3_s"], dtype=np.float64
                ),
                "tau_end_s": np.asarray(updated_db["tau_end_s"], dtype=np.float64),
                "producer": np.asarray(updated_db["producer"]).astype("U32"),
                "xi": np.asarray(updated_db["xi"], dtype=np.float64),
            }
        )

        files = {
            "PAD_Stream_V16E41R3R2_Summary.json": json_bytes(summary_out),
            "V16E41R3R2_Flow_Streamline_Comparison.csv": csv_bytes(flow_rows),
            "V16E41R3R2_Producer_Connectivity_Comparison.csv": csv_bytes(
                producer_rows
            ),
            "V16E41R3R2_Limiter_Cell_Overlap_Support.csv": csv_bytes(
                limiter_support_rows
            ),
            "V16E41R3R2_Frozen_Capacity_Feasibility.json": json_bytes(
                old_capacity_summary
            ),
            "V16E41R3R2_Updated_Capacity_Feasibility.json": json_bytes(
                updated_capacity_summary
            ),
            "V16E41R3R2_Updated_Mobility_Flow_Field.npz": flow_npz,
            "V16E41R3R2_Updated_Pollock_Transport_Database.npz": streamline_npz,
            "V16E41R3R2_Final_Gate_Matrix.csv": csv_bytes(
                [{"gate": k, **v} for k, v in gates.items()]
            ),
            "V16E41R3R2_Final_Closure.json": json_bytes(closure_out),
        }

        immutable_publish(out, files)

        manifest_rows = []
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name != "V16E41R3R2_Artifact_Manifest.csv":
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
                "V16E41R3R2_Artifact_Manifest.csv": csv_bytes(manifest_rows)
            },
        )

        print("\n" + "=" * 152)
        print("PAD-Stream V16E-41-R3-R2: PASS")
        print("=" * 152)
        print(f"{'Status':62}: {STATUS}")
        print(f"{'Input partial step / time':62}: {step} / {time_days:.15g} d")
        print(
            f"{'Updated pressure rel. L2 vs frozen':62}: "
            f"{pressure_rel_l2:.6e}"
        )
        print(
            f"{'Updated flow local/global rel. conservation':62}: "
            f"{conservation['local_relative_l2_error']:.6e} / "
            f"{conservation['global_relative_mismatch']:.6e}"
        )
        print(
            f"{'Updated Pollock seeds / capture fraction':62}: "
            f"{len(seeds)} / {capture_fraction:.12f}"
        )
        print(
            f"{'Limiter inflow fraction frozen -> updated':62}: "
            f"{limiter_inflow_fraction_old:.6e} -> "
            f"{limiter_inflow_fraction_updated:.6e}"
        )
        print(
            f"{'Limiter unique streamlines frozen -> updated':62}: "
            f"{old_support['unique_streamline_count']} -> "
            f"{updated_support['unique_streamline_count']}"
        )
        print(
            f"{'Raw overcapacity cells frozen -> updated':62}: "
            f"{old_over_count} -> {updated_over_count}"
        )
        print(
            f"{'Limiter excess kg frozen -> updated':62}: "
            f"{old_limiter_excess:.6e} -> {updated_limiter_excess:.6e}"
        )
        print(
            f"{'Updated local support reroute feasible':62}: "
            f"{updated_lp['feasible']}"
        )
        print(f"{'Diagnosis':62}: {diagnosis}")
        print(f"{'Output':62}: {out}")
        print(f"{'Next':62}: {NEXT}")
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": MILESTONE,
            "status": "SATURATION_UPDATED_FLOW_STREAMLINE_CAPACITY_FEASIBILITY_AUDIT_BLOCKED",
            "failed_stage": failed_stage,
            "exception": repr(exc),
            "gates": gates,
        }
        data = json_bytes(report)
        p = blocked / "V16E41R3R2_Blocked_Audit.json"
        if p.exists() and p.read_bytes() != data:
            p = blocked / (
                "V16E41R3R2_Blocked_Audit_"
                + hashlib.sha256(data).hexdigest()[:12]
                + ".json"
            )
        p.write_bytes(data)

        print("\n" + "=" * 152)
        print("PAD-Stream V16E-41-R3-R2: BLOCKED")
        print("=" * 152)
        print("Report      :", p)
        print("Failed stage:", failed_stage)
        print("Exception   :", repr(exc))
        return 2


def parse_args() -> argparse.Namespace:
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
