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
import zipfile
from pathlib import Path
from typing import Any

import numpy as np


MILESTONE = "POSTV16-AV2-A2"

STATUS_PASS = (
    "AV2A2_FROZEN_SPATIAL_POROSITY_REALIZATIONS_GENERATED_"
    "PRESSURE_Q_INVARIANCE_CERTIFIED_PORE_KINEMATICS_RECONSTRUCTED_PASS"
)

STATUS_FAIL = (
    "AV2A2_FROZEN_SPATIAL_POROSITY_REALIZATION_OR_PORE_KINEMATICS_"
    "SCIENTIFIC_FAIL_NO_REJECTION_RESEED_OR_ADAPTATION_AUTHORIZED"
)

STATUS_BLOCKED = "AV2A2_TECHNICAL_EXECUTION_BLOCKED"

PROTOCOL_ID = (
    "POSTV16_AV2_A2_FROZEN_POROSITY_GENERATION_AND_PORE_KINEMATICS_EXECUTION_V1"
)

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"

PARENT_AV2A1_COMMIT = "fce3e3de223675a9409e832d7673dbb402e36699"

A1 = (
    "PAD_Stream_POSTV16_AV2_A1_"
    "Spatial_Porosity_Field_Model_and_Split_Registry_Freeze.py"
)
A1_BLOB = "465d493cf6641c8929224d68a15e29aa38f9db69"

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

R8R = "PAD_Stream_V16AR8R_Repaired_Foundation_Case_0001_Final_Assembly_Freeze.py"
R8R_BLOB = "00576330d14efd41ceeb81e2f38b14ba1ef01525"

GAUSS = "SGSIM_50x50x15_GAUSS.csv"
GAUSS_BLOB = "56c87fed8b1e9fd7f6d3451be21a63659e6fa4bf"

PERM = "SGSIM_50x50x15_PERM_MD.csv"
PERM_BLOB = "317dd47d458bc6f880c2e3dc4ec1f69eeb0dd314"

SOURCE_BLOBS = {
    A1: A1_BLOB,
    SG2: SG2_BLOB,
    SG3: SG3_BLOB,
    SG4: SG4_BLOB,
    SG5: SG5_BLOB,
    SG6: SG6_BLOB,
    R8R: R8R_BLOB,
    GAUSS: GAUSS_BLOB,
    PERM: PERM_BLOB,
}

BASE_AV2 = (
    Path("post_v16")
    / RID
    / "POSTV16_AV2_Variable_Porosity"
)

A1_REL = (
    BASE_AV2
    / "POSTV16_AV2_A1_Spatial_Porosity_Field_Model_and_Split_Registry_Freeze"
)

A1_SUMMARY = "PAD_Stream_POSTV16_AV2_A1_Summary.json"
A1_FIELD = "POSTV16_AV2_A1_Frozen_Spatial_Porosity_Field_Model.json"
A1_REGISTRY = "POSTV16_AV2_A1_Frozen_Porosity_Realization_Registry.csv"
A1_ADAPTER = "POSTV16_AV2_A1_Frozen_Pore_Velocity_Pollock_Mapback_Adapter_Contract.json"
A1_FIREWALL = "POSTV16_AV2_A1_Frozen_Train_Validation_LockedOOD_Firewall.json"
A1_DECISION = "POSTV16_AV2_A1_Decision_Contract.json"
A1_MANIFEST = "POSTV16_AV2_A1_Artifact_Manifest.csv"

A1_STATUS = (
    "AV2A1_SPATIAL_POROSITY_FIELD_MODEL_BOUNDS_CORRELATION_"
    "FACE_RULE_AND_SPLIT_REGISTRY_PROSPECTIVELY_FROZEN_NO_FIELD_GENERATION"
)

OUT_REL = (
    BASE_AV2
    / "POSTV16_AV2_A2_Porosity_Realization_and_Pore_Kinematics_Execution"
)

BLOCKED_REL = BASE_AV2 / "POSTV16_AV2_A2_BLOCKED"
FAIL_REL = BASE_AV2 / "POSTV16_AV2_A2_SCIENTIFIC_FAIL"

FOUNDATION_NAME = "V16A_Foundation_Case_0001.npz"
FOUNDATION_SHA = "4239e412ca6e2780f108c8eb1b0252e80a56be305bce48cc58e50d6140b86acc"

GRID = (15, 50, 50)
NZ, NY, NX = GRID

DX_FT = 20.0
DY_FT = 20.0
DZ_FT = 4.0

FT_TO_M = 0.3048
DX_M = DX_FT * FT_TO_M
DY_M = DY_FT * FT_TO_M
DZ_M = DZ_FT * FT_TO_M

AX_M2 = DY_M * DZ_M
AY_M2 = DX_M * DZ_M
AZ_M2 = DX_M * DY_M

PHI_CENTER = 0.20
PHI_HALF_RANGE = 0.10
PHI_SCALE = 2.0
PHI_LOWER = 0.10
PHI_UPPER = 0.30

RHO_LATENT = 0.60

A_MAJOR_FT = 200.0
A_MINOR_FT = 200.0
A_VERT_FT = 15.0
AZIMUTH_DEG = 30.0

EXPECTED_STREAMLINES = 1078
EXPECTED_NODES = 201

REALIZATION_REGISTRY = [
    ("AV2PHI0001", 260201, "TRAIN"),
    ("AV2PHI0002", 260202, "TRAIN"),
    ("AV2PHI0003", 260203, "VALIDATION"),
    ("AV2PHI0004", 260204, "LOCKED_OOD_TEST"),
]

# Prospective recomputation-equivalence tolerances.
PRESSURE_MAX_ABS_TOL_PSI = 1.0e-6
PRESSURE_REL_L2_TOL = 1.0e-10

Q_REL_L2_TOL = 1.0e-10
Q_MAX_ABS_TOL_M3_S = 1.0e-12

LATENT_CORR_ABS_TOL = 1.0e-12

# This is a regression guard only: variable phi must measurably affect TOF.
MIN_TERMINAL_TOF_CHANGE_S = 1.0e-6


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
    p = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return p.stdout.strip()


def git_blob_sha(path: Path, root: Path) -> str:
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
        raise GateError("manifest_empty")
    for fn, expected in manifest.items():
        p = directory / fn
        if not p.is_file():
            raise GateError(f"manifest_missing:{fn}")
        actual = sha256_file(p)
        if actual != expected:
            raise GateError(f"manifest_SHA:{fn}:{actual}:{expected}")
    return manifest


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
        zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as zf:
        for key in sorted(arrays):
            b = io.BytesIO()
            np.save(
                b,
                np.asarray(arrays[key]),
                allow_pickle=False,
            )
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
            raise GateError(f"existing_output_differs:{name}")
        if not p.exists():
            p.write_bytes(data)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError(f"cannot_load_module:{path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def find_named_exact(
    roots: list[Path],
    name: str,
    expected_sha: str,
) -> Path:
    hits: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob(name):
            try:
                if p.is_file() and sha256_file(p) == expected_sha:
                    hits.append(p.resolve())
            except OSError:
                pass
    if not hits:
        raise GateError(f"exact_authority_not_found:{name}:{expected_sha}")
    return sorted(
        set(hits),
        key=lambda p: (len(str(p)), str(p)),
    )[0]


def rel_l2(a: np.ndarray, b: np.ndarray) -> float:
    aa = np.asarray(a, dtype=np.float64)
    bb = np.asarray(b, dtype=np.float64)
    return float(
        np.linalg.norm((aa - bb).ravel())
        / max(np.linalg.norm(bb.ravel()), 1.0e-300)
    )


def max_abs(a: np.ndarray, b: np.ndarray) -> float:
    return float(
        np.max(
            np.abs(
                np.asarray(a, dtype=np.float64)
                - np.asarray(b, dtype=np.float64)
            )
        )
    )


def load_gaussian_field(path: Path) -> np.ndarray:
    values = np.loadtxt(path, skiprows=1, dtype=np.float64)
    if values.size != NZ * NY * NX:
        raise GateError(
            f"Gaussian_cell_count:{values.size}"
        )
    z = values.reshape(GRID, order="C")
    z = (z - np.mean(z)) / np.std(z)
    if not np.all(np.isfinite(z)):
        raise GateError("nonfinite_ZK")
    return z


def covariance_kernel() -> np.ndarray:
    az = np.deg2rad(AZIMUTH_DEG)

    iz = np.arange(NZ)
    iy = np.arange(NY)
    ix = np.arange(NX)

    z = np.minimum(iz, NZ - iz) * DZ_FT
    y = np.minimum(iy, NY - iy) * DY_FT
    x = np.minimum(ix, NX - ix) * DX_FT

    Z, Y, X = np.meshgrid(
        z,
        y,
        x,
        indexing="ij",
    )

    U = X * np.cos(az) + Y * np.sin(az)
    V = -X * np.sin(az) + Y * np.cos(az)

    hstar = np.sqrt(
        (U / A_MAJOR_FT) ** 2
        + (V / A_MINOR_FT) ** 2
        + (Z / A_VERT_FT) ** 2
    )

    return np.exp(-3.0 * hstar)


def generate_standardized_residual(seed: int) -> np.ndarray:
    C = covariance_kernel()
    eig = np.real(np.fft.fftn(C))
    mine = float(np.min(eig))

    if mine < -1.0e-10:
        raise ScientificFail(
            "porosity_residual_covariance_PSD",
            {"seed": seed, "minimum_spectral_eigenvalue": mine},
        )

    eig = np.maximum(eig, 0.0)

    rng = np.random.default_rng(seed)

    white = rng.standard_normal(GRID)

    R = np.real(
        np.fft.ifftn(
            np.fft.fftn(white)
            * np.sqrt(eig)
        )
    )

    std = float(np.std(R))

    if not np.isfinite(std) or std <= 0.0:
        raise ScientificFail(
            "porosity_residual_nonzero_std",
            {"seed": seed, "std": std},
        )

    return (
        (R - np.mean(R))
        / std
    )


def construct_phi(
    z_k: np.ndarray,
    seed: int,
) -> dict[str, np.ndarray | float]:
    R = generate_standardized_residual(seed)

    zk = np.asarray(z_k, dtype=np.float64).ravel()
    rr = np.asarray(R, dtype=np.float64).ravel()

    denom = float(np.dot(zk, zk))
    if denom <= 0.0:
        raise GateError("ZK_zero_norm")

    beta = float(np.dot(rr, zk) / denom)

    r_perp = rr - beta * zk
    r_perp = r_perp.reshape(GRID)

    rp_std = float(np.std(r_perp))
    if not np.isfinite(rp_std) or rp_std <= 0.0:
        raise ScientificFail(
            "orthogonal_porosity_residual_nonzero_std",
            {"seed": seed, "std": rp_std},
        )

    r_perp = (
        (r_perp - np.mean(r_perp))
        / rp_std
    )

    corr_perp = float(
        np.corrcoef(
            z_k.ravel(),
            r_perp.ravel(),
        )[0, 1]
    )

    if abs(corr_perp) > 5.0e-13:
        raise ScientificFail(
            "orthogonalized_residual_correlation_zero",
            {"seed": seed, "corr": corr_perp},
        )

    g_phi = (
        RHO_LATENT * z_k
        + math.sqrt(1.0 - RHO_LATENT**2)
        * r_perp
    )

    g_phi = (
        (g_phi - np.mean(g_phi))
        / np.std(g_phi)
    )

    latent_corr = float(
        np.corrcoef(
            z_k.ravel(),
            g_phi.ravel(),
        )[0, 1]
    )

    phi = (
        PHI_CENTER
        + PHI_HALF_RANGE
        * np.tanh(
            g_phi / PHI_SCALE
        )
    )

    return {
        "residual_orthogonal": r_perp,
        "G_phi": g_phi,
        "phi": phi,
        "latent_corr": latent_corr,
        "residual_corr": corr_perp,
    }


def face_porosity(phi: np.ndarray):
    px = 0.5 * (
        phi[:, :, :-1]
        + phi[:, :, 1:]
    )
    py = 0.5 * (
        phi[:, :-1, :]
        + phi[:, 1:, :]
    )
    pz = 0.5 * (
        phi[:-1, :, :]
        + phi[1:, :, :]
    )
    return px, py, pz


def pore_velocity(
    qx: np.ndarray,
    qy: np.ndarray,
    qz: np.ndarray,
    phi: np.ndarray,
):
    px, py, pz = face_porosity(phi)

    vx = qx / (AX_M2 * px)
    vy = qy / (AY_M2 * py)
    vz = qz / (AZ_M2 * pz)

    return px, py, pz, vx, vy, vz


def flatten_streamline_results(streamlines: list[dict[str, Any]]):
    offsets = [0]
    points = []
    times = []

    for s in streamlines:
        p = np.asarray(s["points_m"], dtype=np.float64)
        t = np.asarray(s["times_s"], dtype=np.float64)

        points.append(p)
        times.append(t)
        offsets.append(offsets[-1] + len(p))

    return {
        "raw_points_m": np.concatenate(points, axis=0),
        "raw_cumulative_times_s": np.concatenate(times, axis=0),
        "raw_offsets": np.asarray(offsets, dtype=np.int64),
    }


def self_test() -> None:
    # Small analytical checks only. No real seed or Foundation data opened.
    x = np.arange(24, dtype=np.float64).reshape(2, 3, 4)
    phi = 0.15 + 0.01 * x

    px, py, pz = face_porosity(phi)

    if px.shape != (2, 3, 3):
        raise RuntimeError("phi_face_x_shape")
    if py.shape != (2, 2, 4):
        raise RuntimeError("phi_face_y_shape")
    if pz.shape != (1, 3, 4):
        raise RuntimeError("phi_face_z_shape")

    if not np.allclose(
        px,
        0.5 * (
            phi[:, :, :-1]
            + phi[:, :, 1:]
        ),
    ):
        raise RuntimeError("phi_face_x_arithmetic")

    rng = np.random.default_rng(260200)
    z = rng.standard_normal(1000)
    z = (z - z.mean()) / z.std()

    r = rng.standard_normal(1000)
    r = (r - r.mean()) / r.std()

    beta = float(np.dot(r, z) / np.dot(z, z))
    rp = r - beta * z
    rp = (rp - rp.mean()) / rp.std()

    g = (
        RHO_LATENT * z
        + math.sqrt(1.0 - RHO_LATENT**2) * rp
    )
    g = (g - g.mean()) / g.std()

    corr = float(np.corrcoef(z, g)[0, 1])

    if abs(corr - RHO_LATENT) > 1.0e-12:
        raise RuntimeError(("latent_corr", corr))

    ph = PHI_CENTER + PHI_HALF_RANGE * np.tanh(g / PHI_SCALE)

    if not (
        np.min(ph) > PHI_LOWER
        and np.max(ph) < PHI_UPPER
    ):
        raise RuntimeError("bounded_phi_transform")

    print("POSTV16-AV2-A2 pore-kinematics execution self-test: PASS")


def main(root: Path, drive: Path) -> int:
    gates: dict[str, dict[str, Any]] = {}
    stage = "preflight"
    field_generation_started = False
    pressure_solve_performed = False
    darcy_flux_recomputed = False
    pollock_execution_started = False
    completed_realizations = 0

    out = drive / OUT_REL
    blocked = drive / BLOCKED_REL
    failed = drive / FAIL_REL

    realization_rows: list[dict[str, Any]] = []

    def gate(
        name: str,
        passed: Any,
        value: Any = None,
    ) -> None:
        ok = bool(passed)
        gates[name] = {
            "passed": ok,
            "value": value,
        }
        suffix = f" — {value}" if value is not None else ""
        print(f"[{'PASS' if ok else 'FAIL'}] {name}{suffix}")
        if not ok:
            raise GateError(name)

    def sci_gate(
        name: str,
        passed: Any,
        value: Any = None,
    ) -> None:
        ok = bool(passed)
        gates[name] = {
            "passed": ok,
            "value": value,
            "scientific_execution_gate": True,
        }
        suffix = f" — {value}" if value is not None else ""
        print(f"[{'PASS' if ok else 'FAIL'}] {name}{suffix}")
        if not ok:
            raise ScientificFail(name, value)

    print("=" * 202)
    print("POSTV16-AV2-A2 — FROZEN SPATIAL-POROSITY GENERATION + PRESSURE/Q INVARIANCE + PORE-KINEMATICS RECONSTRUCTION")
    print("=" * 202)
    print("ONE PREDECLARED FOUR-REALIZATION POROSITY REGISTRY. NO SEED PRETESTING, REJECTION, RESEEDING, OR PARAMETER RETUNING.")
    print("AV1 K / WELLS / CONTROLS / EOS / RELPERM / CAPILLARY REMAIN FROZEN.")
    print("PRESSURE AND DARCY Q ARE RECOMPUTED FROM THE UNCHANGED AV1 FLOW OPERATOR AND COMPARED TO FOUNDATION CASE 0001.")
    print("VARIABLE-PHI PORE VELOCITIES, EXACT POLLOCK PATHS, AND 201-NODE TOF COORDINATES ARE THEN REBUILT.")
    print("NO TRANSPORT TARGET GENERATION. NO TRAINING. NO INFERENCE. NO MAPBACK. NO CMG.\n")

    try:
        root = root.resolve()
        drive = drive.resolve()

        parent = git_text(root, "rev-parse", "HEAD^")
        status = git_text(root, "status", "--porcelain")

        gate(
            "repository_parent_is_AV2A1_commit",
            parent == PARENT_AV2A1_COMMIT,
            parent,
        )
        gate(
            "repository_clean",
            status == "",
            repr(status),
        )

        for fn, expected in SOURCE_BLOBS.items():
            p = root / fn
            actual = (
                git_blob_sha(p, root)
                if p.is_file()
                else "missing"
            )
            gate(
                f"{Path(fn).stem}_git_blob_exact",
                actual == expected,
                actual,
            )

        # ==============================================================
        # Bind A1 contract exactly.
        # ==============================================================

        stage = "AV2A1_contract_binding"

        a1 = drive / A1_REL

        gate(
            "AV2A1_output_present",
            a1.is_dir(),
            str(a1),
        )

        a1_manifest = verify_manifest(
            a1,
            A1_MANIFEST,
        )

        gate(
            "AV2A1_manifest_SHA_closure",
            True,
            len(a1_manifest),
        )

        s1 = load_json(a1 / A1_SUMMARY)
        field1 = load_json(a1 / A1_FIELD)
        adapter1 = load_json(a1 / A1_ADAPTER)
        firewall1 = load_json(a1 / A1_FIREWALL)
        decision1 = load_json(a1 / A1_DECISION)
        registry1 = read_csv(a1 / A1_REGISTRY)

        gate(
            "AV2A1_status_exact",
            s1["status"] == A1_STATUS,
            s1["status"],
        )

        gate(
            "AV2A1_porosity_model_frozen",
            s1["porosity_model_frozen"] is True,
        )

        gate(
            "AV2A1_A2_authorized",
            decision1["A2_authorized"] is True,
        )

        gate(
            "AV2A1_next_id_exact",
            decision1["next"]["milestone"]
            == "POSTV16-AV2-A2",
        )

        gate(
            "AV2A1_AV1_K_unchanged",
            s1["AV1_K_unchanged"] is True,
        )

        gate(
            "AV2A1_no_global_phi_rescale",
            s1["global_porosity_rescale"] is False,
        )

        gate(
            "AV2A1_no_global_PV_rescale",
            s1["global_pore_volume_rescale"] is False,
        )

        gate(
            "AV2A1_latent_corr_exact",
            float(s1["latent_K_phi_correlation"])
            == RHO_LATENT,
        )

        gate(
            "AV2A1_face_phi_rule_exact",
            s1["face_porosity_rule"]
            == "arithmetic_mean_of_adjacent_cell_porosity",
        )

        frozen_registry = [
            (
                r["porosity_realization_id"],
                int(r["seed"]),
                r["partition"],
            )
            for r in registry1
        ]

        gate(
            "AV2A1_realization_registry_exact",
            frozen_registry == REALIZATION_REGISTRY,
            frozen_registry,
        )

        gate(
            "AV2A1_locked_OOD_target_access_forbidden",
            firewall1[
                "locked_OOD_target_access_before_checkpoint_freeze"
            ]
            is False,
        )

        gate(
            "AV2A1_retrace_required",
            adapter1["Pollock_and_TOF"]["retrace_required_in_A2"]
            is True,
        )

        gate(
            "AV2A1_pressure_Q_invariance_not_preclaimed",
            adapter1[
                "pressure_and_Darcy_expectation"
            ]["invariance_not_preclaimed_in_A1"]
            is True,
        )

        # ==============================================================
        # Bind exact Foundation Case.
        # ==============================================================

        stage = "Foundation0001_binding"

        foundation = find_named_exact(
            [root, drive],
            FOUNDATION_NAME,
            FOUNDATION_SHA,
        )

        gate(
            "Foundation0001_SHA_exact",
            sha256_file(foundation) == FOUNDATION_SHA,
            str(foundation),
        )

        with np.load(
            foundation,
            allow_pickle=False,
        ) as z:
            required = [
                "Kx",
                "Ky",
                "Kz",
                "porosity",
                "pressure",
                "Qx",
                "Qy",
                "Qz",
                "streamline_xyz",
                "pollock_tof",
                "streamline_weight",
            ]

            gate(
                "Foundation0001_required_arrays_present",
                set(required).issubset(set(z.files)),
                sorted(z.files),
            )

            d = {
                k: np.asarray(z[k]).copy()
                for k in required
            }

        gate(
            "Foundation0001_grid_shape",
            d["Kx"].shape == GRID,
            d["Kx"].shape,
        )

        gate(
            "Foundation0001_constant_phi_0p20",
            np.array_equal(
                np.asarray(d["porosity"], dtype=np.float64),
                np.full(GRID, 0.20, dtype=np.float64),
            ),
        )

        gate(
            "Foundation0001_streamline_shape",
            d["streamline_xyz"].shape
            == (
                EXPECTED_STREAMLINES,
                EXPECTED_NODES,
                3,
            ),
            d["streamline_xyz"].shape,
        )

        gate(
            "Foundation0001_TOF_shape",
            d["pollock_tof"].shape
            == (
                EXPECTED_STREAMLINES,
                EXPECTED_NODES,
            ),
            d["pollock_tof"].shape,
        )

        # ==============================================================
        # Import exact frozen physics implementations.
        # ==============================================================

        stage = "physics_module_binding"

        sg2 = load_module(
            root / SG2,
            "av2a2_sg2",
        )

        sg3 = load_module(
            root / SG3,
            "av2a2_sg3",
        )

        sg4 = load_module(
            root / SG4,
            "av2a2_sg4",
        )

        sg5 = load_module(
            root / SG5,
            "av2a2_sg5",
        )

        sg6 = load_module(
            root / SG6,
            "av2a2_sg6",
        )

        # ==============================================================
        # Exact recomputation of pressure and Darcy Q.
        # ==============================================================

        stage = "pressure_Q_recomputation"

        Kx = np.asarray(
            d["Kx"],
            dtype=np.float64,
        )

        Ky = np.asarray(
            d["Ky"],
            dtype=np.float64,
        )

        Kz = np.asarray(
            d["Kz"],
            dtype=np.float64,
        )

        kfx, kfy, kfz = sg2.build_face_permeabilities(
            Kx,
            Ky,
            Kz,
        )

        tx, ty, tz = sg3.construct_si_transmissibilities(
            kfx,
            kfy,
            kfz,
        )

        A, b, producer_wi = sg3.assemble_pressure_system(
            Kx,
            tx,
            ty,
            tz,
        )

        pressure_solve_performed = True

        p_pa, p_psi = sg3.solve_pressure(
            A,
            b,
        )

        producer_rates, total_prod = sg3.calculate_well_rates(
            p_psi,
            producer_wi,
        )

        pressure_validation = sg3.validate_solution(
            A,
            b,
            p_pa,
            p_psi,
            producer_rates,
            total_prod,
        )

        # Independent SG4 reconstruction from the recomputed pressure.
        tx4, ty4, tz4 = sg4.construct_si_transmissibilities(
            kfx,
            kfy,
            kfz,
        )

        sci_gate(
            "SG3_SG4_Tx_identity",
            np.array_equal(tx, tx4),
        )
        sci_gate(
            "SG3_SG4_Ty_identity",
            np.array_equal(ty, ty4),
        )
        sci_gate(
            "SG3_SG4_Tz_identity",
            np.array_equal(tz, tz4),
        )

        qx, qy, qz = sg4.compute_face_fluxes(
            p_psi,
            tx4,
            ty4,
            tz4,
        )

        darcy_flux_recomputed = True

        div = sg4.compute_flux_divergence(
            qx,
            qy,
            qz,
        )

        well_source, producer_q = sg4.construct_expected_well_rates(
            Kx,
            p_psi,
        )

        flux_validation = sg4.validate_conservation(
            qx,
            qy,
            qz,
            div,
            well_source,
        )

        p_max = max_abs(
            p_psi,
            d["pressure"],
        )

        p_rel = rel_l2(
            p_psi,
            d["pressure"],
        )

        qx_max = max_abs(
            qx,
            d["Qx"],
        )
        qy_max = max_abs(
            qy,
            d["Qy"],
        )
        qz_max = max_abs(
            qz,
            d["Qz"],
        )

        qx_rel = rel_l2(
            qx,
            d["Qx"],
        )
        qy_rel = rel_l2(
            qy,
            d["Qy"],
        )
        qz_rel = rel_l2(
            qz,
            d["Qz"],
        )

        sci_gate(
            "pressure_recompute_max_abs_within_tolerance",
            p_max <= PRESSURE_MAX_ABS_TOL_PSI,
            p_max,
        )

        sci_gate(
            "pressure_recompute_relative_L2_within_tolerance",
            p_rel <= PRESSURE_REL_L2_TOL,
            p_rel,
        )

        for name, ma, rr in [
            ("Qx", qx_max, qx_rel),
            ("Qy", qy_max, qy_rel),
            ("Qz", qz_max, qz_rel),
        ]:
            sci_gate(
                f"{name}_recompute_max_abs_within_tolerance",
                ma <= Q_MAX_ABS_TOL_M3_S,
                ma,
            )

            sci_gate(
                f"{name}_recompute_relative_L2_within_tolerance",
                rr <= Q_REL_L2_TOL,
                rr,
            )

        flow_audit = {
            "pressure": {
                "max_abs_difference_psi": p_max,
                "relative_L2_difference": p_rel,
                "max_abs_tolerance_psi": PRESSURE_MAX_ABS_TOL_PSI,
                "relative_L2_tolerance": PRESSURE_REL_L2_TOL,
                "SG3_validation": pressure_validation,
            },
            "Darcy_Q": {
                "Qx_max_abs_difference_m3_s": qx_max,
                "Qy_max_abs_difference_m3_s": qy_max,
                "Qz_max_abs_difference_m3_s": qz_max,
                "Qx_relative_L2_difference": qx_rel,
                "Qy_relative_L2_difference": qy_rel,
                "Qz_relative_L2_difference": qz_rel,
                "max_abs_tolerance_m3_s": Q_MAX_ABS_TOL_M3_S,
                "relative_L2_tolerance": Q_REL_L2_TOL,
                "SG4_validation": flux_validation,
            },
            "interpretation": (
                "With AV1 permeability, grid, fluid properties, gravity, and "
                "well controls unchanged, the finite-volume pressure and Darcy "
                "volumetric-flow operators do not depend directly on porosity. "
                "A2 recomputes both and certifies numerical equivalence to "
                "Foundation Case 0001 before variable-porosity pore kinematics."
            ),
        }

        # ==============================================================
        # Freeze/load exact permeability latent anchor.
        # ==============================================================

        stage = "porosity_latent_anchor"

        z_k = load_gaussian_field(
            root / GAUSS
        )

        gate(
            "standardized_ZK_mean_zero",
            abs(float(np.mean(z_k))) <= 1.0e-12,
            float(np.mean(z_k)),
        )

        gate(
            "standardized_ZK_std_one",
            abs(float(np.std(z_k)) - 1.0) <= 1.0e-12,
            float(np.std(z_k)),
        )

        K_for_corr = np.asarray(
            d["Kx"],
            dtype=np.float64,
        )

        # ==============================================================
        # Injector seeding is a Q-only authority and therefore identical
        # for all four porosity realizations.
        # ==============================================================

        stage = "frozen_seed_binding"

        faces, seeds = sg5.build_seeds(
            qx,
            qy,
            qz,
        )

        sci_gate(
            "exact_seed_count_1078",
            len(seeds) == EXPECTED_STREAMLINES,
            len(seeds),
        )

        seed_weights = np.asarray(
            [
                s["weight_m3_s"]
                for s in seeds
            ],
            dtype=np.float64,
        )

        sci_gate(
            "seed_weights_match_Foundation_streamline_weights",
            np.allclose(
                seed_weights,
                np.asarray(
                    d["streamline_weight"],
                    dtype=np.float64,
                ),
                rtol=1.0e-12,
                atol=1.0e-16,
            ),
            max_abs(
                seed_weights,
                d["streamline_weight"],
            ),
        )

        outgoing_q = float(
            sum(
                f["q_m3_s"]
                for f in faces
            )
        )

        seed_q = float(
            np.sum(seed_weights)
        )

        sci_gate(
            "seed_weight_flux_closure",
            np.isclose(
                outgoing_q,
                seed_q,
                rtol=1.0e-12,
                atol=1.0e-15,
            ),
            {
                "outgoing_q_m3_s": outgoing_q,
                "seed_q_m3_s": seed_q,
            },
        )

        # ==============================================================
        # Execute exact frozen realization registry.
        # ==============================================================

        stage = "porosity_and_Pollock_execution"

        files: dict[str, bytes] = {}

        av1_xyz = np.asarray(
            d["streamline_xyz"],
            dtype=np.float64,
        )

        av1_tof = np.asarray(
            d["pollock_tof"],
            dtype=np.float64,
        )

        av1_terminal = av1_tof[:, -1]

        for ridx, (
            rid,
            seed,
            partition,
        ) in enumerate(
            REALIZATION_REGISTRY,
            start=1,
        ):
            print("\n" + "=" * 202)
            print(
                f"AV2-A2 POROSITY REALIZATION {ridx}/4 — "
                f"{rid} / seed={seed} / partition={partition}"
            )
            print("=" * 202)

            field_generation_started = True

            generated = construct_phi(
                z_k,
                seed,
            )

            phi = np.asarray(
                generated["phi"],
                dtype=np.float64,
            )

            G_phi = np.asarray(
                generated["G_phi"],
                dtype=np.float64,
            )

            r_perp = np.asarray(
                generated["residual_orthogonal"],
                dtype=np.float64,
            )

            latent_corr = float(
                generated["latent_corr"]
            )

            residual_corr = float(
                generated["residual_corr"]
            )

            sci_gate(
                f"{rid}_shape_exact",
                phi.shape == GRID,
                phi.shape,
            )

            sci_gate(
                f"{rid}_finite",
                np.all(np.isfinite(phi)),
            )

            phi_min = float(np.min(phi))
            phi_max = float(np.max(phi))
            phi_mean = float(np.mean(phi))
            phi_std = float(np.std(phi))

            sci_gate(
                f"{rid}_strict_lower_bound",
                phi_min > PHI_LOWER,
                phi_min,
            )

            sci_gate(
                f"{rid}_strict_upper_bound",
                phi_max < PHI_UPPER,
                phi_max,
            )

            sci_gate(
                f"{rid}_nonconstant",
                phi_std > 0.0,
                phi_std,
            )

            sci_gate(
                f"{rid}_latent_K_phi_corr_exact",
                abs(
                    latent_corr
                    - RHO_LATENT
                )
                <= LATENT_CORR_ABS_TOL,
                latent_corr,
            )

            sci_gate(
                f"{rid}_orthogonal_residual_corr_zero",
                abs(residual_corr)
                <= 5.0e-13,
                residual_corr,
            )

            phi_k_corr = float(
                np.corrcoef(
                    phi.ravel(),
                    K_for_corr.ravel(),
                )[0, 1]
            )

            pv_ratio_to_AV1 = float(
                np.sum(phi)
                / (
                    PHI_CENTER
                    * phi.size
                )
            )

            px, py, pz, vx, vy, vz = pore_velocity(
                qx,
                qy,
                qz,
                phi,
            )

            sci_gate(
                f"{rid}_face_phi_positive",
                (
                    np.all(px > PHI_LOWER)
                    and np.all(py > PHI_LOWER)
                    and np.all(pz > PHI_LOWER)
                ),
            )

            sci_gate(
                f"{rid}_pore_velocity_finite",
                (
                    np.all(np.isfinite(vx))
                    and np.all(np.isfinite(vy))
                    and np.all(np.isfinite(vz))
                ),
            )

            pollock_execution_started = True

            streamlines = sg5.trace_streamlines(
                seeds,
                vx,
                vy,
                vz,
            )

            statuses = np.asarray(
                [
                    s["status"]
                    for s in streamlines
                ],
                dtype="U32",
            )

            producers = np.asarray(
                [
                    s["producer"]
                    for s in streamlines
                ],
                dtype="U32",
            )

            producer_count = int(
                np.sum(
                    statuses == "PRODUCER"
                )
            )

            boundary_count = int(
                np.sum(
                    statuses == "BOUNDARY_EXIT"
                )
            )

            stagnation_count = int(
                np.sum(
                    statuses == "STAGNATION"
                )
            )

            loop_count = int(
                np.sum(
                    statuses == "CELL_LOOP"
                )
            )

            maxstep_count = int(
                np.sum(
                    statuses == "MAX_STEPS"
                )
            )

            sci_gate(
                f"{rid}_all_1078_streamlines_producer_captured",
                producer_count == EXPECTED_STREAMLINES,
                {
                    "producer": producer_count,
                    "boundary": boundary_count,
                    "stagnation": stagnation_count,
                    "loop": loop_count,
                    "maxstep": maxstep_count,
                },
            )

            sci_gate(
                f"{rid}_all_four_producers_represented",
                all(
                    np.any(
                        producers
                        == name
                    )
                    for name
                    in sg5.PRODUCERS
                ),
                sorted(
                    set(
                        str(x)
                        for x in producers.tolist()
                    )
                ),
            )

            sg6_streamlines = []

            for sid, s in enumerate(
                streamlines
            ):
                sg6_streamlines.append(
                    {
                        "id": sid,
                        "points_m": np.asarray(
                            s["points_m"],
                            dtype=np.float64,
                        ),
                        "tau_s": np.asarray(
                            s["times_s"],
                            dtype=np.float64,
                        ),
                        "weight_m3_s": float(
                            s["weight_m3_s"]
                        ),
                        "tau_end_s": float(
                            s["travel_time_s"]
                        ),
                        "status": str(
                            s["status"]
                        ),
                        "producer": str(
                            s["producer"]
                        ),
                    }
                )

            db = sg6.build_transport_database(
                sg6_streamlines
            )

            sg6.validate_transport(
                db
            )

            xyz = np.asarray(
                db["xyz_m"],
                dtype=np.float64,
            )

            tof = np.asarray(
                db["tau_s"],
                dtype=np.float64,
            )

            weights = np.asarray(
                db["weights_m3_s"],
                dtype=np.float64,
            )

            tau_end = np.asarray(
                db["tau_end_s"],
                dtype=np.float64,
            )

            prod = np.asarray(
                db["producer"],
                dtype="U32",
            )

            sci_gate(
                f"{rid}_transport_XYZ_shape_exact",
                xyz.shape
                == (
                    EXPECTED_STREAMLINES,
                    EXPECTED_NODES,
                    3,
                ),
                xyz.shape,
            )

            sci_gate(
                f"{rid}_transport_TOF_shape_exact",
                tof.shape
                == (
                    EXPECTED_STREAMLINES,
                    EXPECTED_NODES,
                ),
                tof.shape,
            )

            sci_gate(
                f"{rid}_streamline_weights_preserved",
                np.allclose(
                    weights,
                    seed_weights,
                    rtol=1.0e-12,
                    atol=1.0e-16,
                ),
                max_abs(
                    weights,
                    seed_weights,
                ),
            )

            terminal_change_max = max_abs(
                tau_end,
                av1_terminal,
            )

            sci_gate(
                f"{rid}_variable_phi_changes_terminal_TOF",
                terminal_change_max
                > MIN_TERMINAL_TOF_CHANGE_S,
                terminal_change_max,
            )

            xyz_change_max = max_abs(
                xyz,
                av1_xyz,
            )

            tof_grid_change_max = max_abs(
                tof,
                av1_tof,
            )

            raw = flatten_streamline_results(
                streamlines
            )

            arrays = {
                "porosity": phi,
                "G_phi": G_phi,
                "porosity_residual_orthogonal": r_perp,
                "phi_face_x": px,
                "phi_face_y": py,
                "phi_face_z": pz,
                "Vx_m_s": vx,
                "Vy_m_s": vy,
                "Vz_m_s": vz,
                "streamline_xyz_m": xyz,
                "pollock_tof_s": tof,
                "terminal_pollock_tof_s": tau_end,
                "streamline_weight_m3_s": weights,
                "producer": prod,
                "streamline_id": np.asarray(
                    db["streamline_id"],
                    dtype=np.int64,
                ),
                "xi": np.asarray(
                    db["xi"],
                    dtype=np.float64,
                ),
                "path_length_m": np.asarray(
                    db["path_length_m"],
                    dtype=np.float64,
                ),
                "seed": np.asarray(
                    [seed],
                    dtype=np.int64,
                ),
                "partition": np.asarray(
                    [partition],
                    dtype="U32",
                ),
                "porosity_realization_id": np.asarray(
                    [rid],
                    dtype="U32",
                ),
                **raw,
            }

            artifact_name = (
                f"POSTV16_AV2_A2_{rid}_"
                "Variable_Porosity_Pore_Kinematics.npz"
            )

            files[artifact_name] = deterministic_npz_bytes(
                arrays
            )

            realization_rows.append(
                {
                    "porosity_realization_id": rid,
                    "seed": seed,
                    "partition": partition,
                    "phi_min": phi_min,
                    "phi_max": phi_max,
                    "phi_mean": phi_mean,
                    "phi_std": phi_std,
                    "latent_K_phi_correlation": latent_corr,
                    "physical_K_phi_correlation": phi_k_corr,
                    "total_pore_volume_ratio_to_AV1_constant_phi": pv_ratio_to_AV1,
                    "streamline_count": int(len(weights)),
                    "producer_captured_count": producer_count,
                    "boundary_exit_count": boundary_count,
                    "stagnation_count": stagnation_count,
                    "cell_loop_count": loop_count,
                    "maxstep_count": maxstep_count,
                    "terminal_TOF_min_days": float(
                        np.min(tau_end)
                        / sg6.DAY_TO_S
                    ),
                    "terminal_TOF_mean_days": float(
                        np.mean(tau_end)
                        / sg6.DAY_TO_S
                    ),
                    "terminal_TOF_max_days": float(
                        np.max(tau_end)
                        / sg6.DAY_TO_S
                    ),
                    "max_abs_terminal_TOF_change_vs_AV1_s": terminal_change_max,
                    "max_abs_201node_TOF_change_vs_AV1_s": tof_grid_change_max,
                    "max_abs_201node_XYZ_change_vs_AV1_m": xyz_change_max,
                    "weight_sum_m3_day": float(
                        np.sum(weights)
                        * sg6.DAY_TO_S
                    ),
                    "artifact": artifact_name,
                }
            )

            completed_realizations += 1

        sci_gate(
            "all_four_frozen_porosity_realizations_completed",
            completed_realizations == 4,
            completed_realizations,
        )

        # No seed/realization adaptation was permitted or performed.
        gate(
            "no_seed_pretesting",
            True,
        )
        gate(
            "no_realization_rejection",
            True,
        )
        gate(
            "no_reseeding",
            True,
        )
        gate(
            "no_porosity_parameter_retuning",
            True,
        )
        gate(
            "no_transport_target_generation",
            True,
        )
        gate(
            "no_training",
            True,
        )
        gate(
            "no_inference",
            True,
        )
        gate(
            "no_mapback",
            True,
        )
        gate(
            "no_CMG",
            True,
        )

        # ==============================================================
        # Final decision.
        # ==============================================================

        decision = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "protocol_id": PROTOCOL_ID,
            "scientific_execution_pass": True,
            "porosity_realization_count": 4,
            "pressure_recomputed": True,
            "Darcy_Q_recomputed": True,
            "pressure_Q_invariance_certified": True,
            "variable_phi_pore_velocity_recomputed": True,
            "Pollock_retraced": True,
            "TOF_recomputed": True,
            "all_1078_streamlines_captured_for_all_realizations": True,
            "AV1_permeability_modified": False,
            "seed_pretesting": False,
            "realization_rejection": False,
            "reseeding": False,
            "porosity_parameter_retuning": False,
            "transport_target_generation": False,
            "training": False,
            "inference": False,
            "mapback": False,
            "CMG_validation": False,
            "locked_OOD_transport_target_opened": False,
            "authorized_claim": (
                "Under the frozen AV2-A1 porosity model and four predeclared "
                "porosity seeds, the unchanged AV1 finite-volume pressure and "
                "Darcy volumetric-flow solution is numerically reproduced within "
                "the prospectively frozen A2 tolerances, while local variable "
                "porosity changes pore velocity and therefore requires/reproduces "
                "new exact Pollock/TOF kinematics for all four realizations."
            ),
            "claim_boundary": (
                "A2 does not establish variable-porosity transport-model accuracy, "
                "locked-OOD predictive performance, conservative grid mapback, "
                "AV2 end-to-end deployment, or external/CMG validation."
            ),
            "next": {
                "milestone": "POSTV16-AV2-A3",
                "name": (
                    "Variable-Porosity Transport Teacher/Dataset Assembly and "
                    "PI-RNN Objective/Normalization/Architecture/Split Contract Freeze"
                ),
                "authorized": True,
                "locked_OOD_transport_target_access": False,
            },
        }

        summary = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "protocol_id": PROTOCOL_ID,
            "Foundation0001_SHA256": FOUNDATION_SHA,
            "pressure_Q_invariance": True,
            "pressure_max_abs_difference_psi": p_max,
            "pressure_relative_L2_difference": p_rel,
            "Qx_relative_L2_difference": qx_rel,
            "Qy_relative_L2_difference": qy_rel,
            "Qz_relative_L2_difference": qz_rel,
            "porosity_realizations_completed": completed_realizations,
            "TRAIN_realizations": 2,
            "VALIDATION_realizations": 1,
            "LOCKED_OOD_realizations": 1,
            "all_streamlines_captured_each_realization": True,
            "transport_target_generated": False,
            "training": False,
            "inference": False,
            "mapback": False,
            "CMG_validation": False,
            "next": decision["next"],
        }

        files.update(
            {
                "PAD_Stream_POSTV16_AV2_A2_Summary.json":
                    json_bytes(summary),
                "POSTV16_AV2_A2_Pressure_Q_Invariance_Audit.json":
                    json_bytes(flow_audit),
                "POSTV16_AV2_A2_By_Porosity_Realization_Diagnostics.csv":
                    csv_bytes(realization_rows),
                "POSTV16_AV2_A2_Decision_Contract.json":
                    json_bytes(decision),
                "POSTV16_AV2_A2_Final_Gate_Matrix.csv":
                    csv_bytes(
                        [
                            {
                                "gate": k,
                                **v,
                            }
                            for k, v
                            in gates.items()
                        ]
                    ),
            }
        )

        immutable_publish(
            out,
            files,
        )

        manifest_rows = []

        for q in sorted(
            out.iterdir()
        ):
            if (
                q.is_file()
                and q.name
                !=
                "POSTV16_AV2_A2_Artifact_Manifest.csv"
            ):
                manifest_rows.append(
                    {
                        "file": q.name,
                        "sha256": sha256_file(q),
                        "bytes": q.stat().st_size,
                    }
                )

        immutable_publish(
            out,
            {
                "POSTV16_AV2_A2_Artifact_Manifest.csv":
                    csv_bytes(
                        manifest_rows
                    )
            },
        )

        print("\n" + "=" * 202)
        print("POSTV16-AV2-A2: PASS")
        print("=" * 202)
        print(f"{'Status':120}: {STATUS_PASS}")
        print(f"{'Pressure max abs difference [psi]':120}: {p_max:.12e}")
        print(f"{'Pressure relative L2 difference':120}: {p_rel:.12e}")
        print(f"{'Qx / Qy / Qz relative L2 difference':120}: {qx_rel:.12e} / {qy_rel:.12e} / {qz_rel:.12e}")
        print(f"{'Pressure/Q invariance certified':120}: True")
        print(f"{'Porosity realizations completed':120}: {completed_realizations} / 4")
        print(f"{'All 1078 streamlines producer-captured for all realizations':120}: True")
        print(f"{'Variable-phi TOF response nonzero for all realizations':120}: True")
        print(f"{'Seed pretesting / rejection / reseeding':120}: False / False / False")
        print(f"{'Transport target generation / training / inference / mapback':120}: False / False / False / False")
        print(f"{'CMG validation':120}: False")
        print(f"{'Locked-OOD transport target opened':120}: False")
        print(f"{'Next milestone authorized':120}: True")
        print(f"{'NEXT':120}: POSTV16-AV2-A3 — variable-phi teacher/dataset + PI-RNN protocol freeze")
        print("=" * 202)

        return 0

    except ScientificFail as exc:
        failed.mkdir(
            parents=True,
            exist_ok=True,
        )

        report = {
            "milestone": MILESTONE,
            "status": STATUS_FAIL,
            "failed_stage": stage,
            "failed_gate": exc.gate,
            "detail": exc.detail,
            "gates": gates,
            "field_generation_started": field_generation_started,
            "pressure_solve_performed": pressure_solve_performed,
            "Darcy_flux_recomputed": darcy_flux_recomputed,
            "Pollock_execution_started": pollock_execution_started,
            "completed_realizations": completed_realizations,
            "seed_pretesting": False,
            "realization_rejection": False,
            "reseeding": False,
            "retuning": False,
            "training": False,
            "inference": False,
            "mapback": False,
            "CMG_validation": False,
            "next_milestone_authorized": False,
            "next_action": (
                "Freeze and interpret this A2 scientific failure. "
                "Do not reject the realization, change its seed, or alter the "
                "A1 porosity model based on the observed result."
            ),
        }

        data = json_bytes(report)

        q = (
            failed
            / "POSTV16_AV2_A2_Scientific_Fail_Report.json"
        )

        if (
            q.exists()
            and q.read_bytes() != data
        ):
            suffix = hashlib.sha256(
                data
            ).hexdigest()[:12]
            q = (
                failed
                / f"POSTV16_AV2_A2_Scientific_Fail_Report_{suffix}.json"
            )

        if not q.exists():
            q.write_bytes(data)

        print("\n" + "=" * 202)
        print("POSTV16-AV2-A2: SCIENTIFIC FAIL")
        print("=" * 202)
        print("Failed stage:", stage)
        print("Failed gate :", exc.gate)
        print("Detail      :", exc.detail)
        print("Report      :", q)
        print("NO REJECTION / RESEED / RETUNING IS AUTHORIZED.")
        print("POSTV16-AV2-A3 IS NOT AUTHORIZED.")

        return 3

    except Exception as exc:
        blocked.mkdir(
            parents=True,
            exist_ok=True,
        )

        report = {
            "milestone": MILESTONE,
            "status": STATUS_BLOCKED,
            "failed_stage": stage,
            "exception": repr(exc),
            "gates": gates,
            "field_generation_started": field_generation_started,
            "pressure_solve_performed": pressure_solve_performed,
            "Darcy_flux_recomputed": darcy_flux_recomputed,
            "Pollock_execution_started": pollock_execution_started,
            "completed_realizations": completed_realizations,
            "training": False,
            "inference": False,
            "mapback": False,
            "CMG_validation": False,
            "next_milestone_authorized": False,
            "next_action": (
                "Audit only the technical A2 failure. "
                "Do not alter A1 seeds or porosity parameters."
            ),
        }

        data = json_bytes(report)

        q = blocked / "POSTV16_AV2_A2_Blocked_Report.json"

        if (
            q.exists()
            and q.read_bytes() != data
        ):
            suffix = hashlib.sha256(
                data
            ).hexdigest()[:12]
            q = (
                blocked
                / f"POSTV16_AV2_A2_Blocked_Report_{suffix}.json"
            )

        if not q.exists():
            q.write_bytes(data)

        print("\n" + "=" * 202)
        print("POSTV16-AV2-A2: BLOCKED")
        print("=" * 202)
        print("Failed stage:", stage)
        print("Exception   :", repr(exc))
        print("Report      :", q)

        return 2


def parse_args():
    p = argparse.ArgumentParser()

    p.add_argument(
        "--project-root",
        type=Path,
        default=Path("."),
    )

    p.add_argument(
        "--drive-root",
        type=Path,
        default=Path(
            "/content/drive/MyDrive/PAD_Stream_Compute"
        ),
    )

    p.add_argument(
        "--self-test",
        action="store_true",
    )

    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.self_test:
        self_test()
        raise SystemExit(0)

    raise SystemExit(
        main(
            args.project_root,
            args.drive_root,
        )
    )
