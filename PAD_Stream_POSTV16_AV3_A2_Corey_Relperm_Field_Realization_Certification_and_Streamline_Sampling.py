#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import subprocess
import zipfile
from pathlib import Path
from typing import Any

import numpy as np


MILESTONE = "POSTV16-AV3-A2"
PROTOCOL_ID = (
    "POSTV16_AV3_A2_COREY_RELPERM_FIELD_REALIZATION_CERTIFICATION_"
    "AND_FROZEN_STREAMLINE_SAMPLING_V1"
)

STATUS_PASS = (
    "AV3A2_FROZEN_COREY_RELPERM_REALIZATIONS_GENERATED_CERTIFIED_"
    "AND_SAMPLED_TO_FROZEN_AV2_STREAMLINES_PASS"
)

STATUS_FAIL = (
    "AV3A2_FROZEN_COREY_RELPERM_REALIZATION_OR_CERTIFICATION_"
    "SCIENTIFIC_FAIL_NO_REJECTION_RESEED_OR_RETUNING_AUTHORIZED"
)

STATUS_BLOCKED = "AV3A2_TECHNICAL_EXECUTION_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT_A1_COMMIT = "2d38e66eec34a9693ae0daaccb3dc584dffe576f"

# --------------------------------------------------------------------------------------------------
# Exact source lineage.
# --------------------------------------------------------------------------------------------------

A1 = "PAD_Stream_POSTV16_AV3_A1_Corey_Relperm_Parameter_Field_Model_and_Split_Registry_Freeze.py"
A1_BLOB = "fb3b77b89ab3d1b12a09f967a476c4ecfcda0e33"

AV2A2 = "PAD_Stream_POSTV16_AV2_A2_Porosity_Realization_and_Pore_Kinematics_Execution.py"
AV2A2_BLOB = "f141b07f0424d29a7996c089a76dbe7128af5132"

C2 = "PAD_Stream_V16C2_Multi_Coordinate_Streamline_Transport_Database_Assembly.py"
C2_BLOB = "21ff44de456102772c99f7ddc80898c9139a76db"

GAUSS = "SGSIM_50x50x15_GAUSS.csv"
GAUSS_BLOB = "56c87fed8b1e9fd7f6d3451be21a63659e6fa4bf"

PERM = "SGSIM_50x50x15_PERM_MD.csv"
PERM_BLOB = "317dd47d458bc6f880c2e3dc4ec1f69eeb0dd314"

SOURCE_BLOBS = {
    A1: A1_BLOB,
    AV2A2: AV2A2_BLOB,
    C2: C2_BLOB,
    GAUSS: GAUSS_BLOB,
    PERM: PERM_BLOB,
}

# --------------------------------------------------------------------------------------------------
# Drive authorities.
# --------------------------------------------------------------------------------------------------

BASE_AV3 = Path("post_v16") / RID / "POSTV16_AV3_Corey_Relperm_Heterogeneity"

A1_REL = BASE_AV3 / "POSTV16_AV3_A1_Corey_Relperm_Parameter_Field_Model_and_Split_Registry_Freeze"
A1_SUMMARY = "PAD_Stream_POSTV16_AV3_A1_Summary.json"
A1_PARAMETERS = "POSTV16_AV3_A1_Selected_Parameter_Subset_and_Bounds.json"
A1_FIELD = "POSTV16_AV3_A1_Field_Model_and_Correlation_Contract.json"
A1_REGISTRY = "POSTV16_AV3_A1_Frozen_Corey_Relperm_Realization_Registry.csv"
A1_CHANNELS = "POSTV16_AV3_A1_Predictor_Channel_Contract.json"
A1_SPLIT = "POSTV16_AV3_A1_Split_and_Leakage_Firewall.json"
A1_HANDOFF = "POSTV16_AV3_A1_A2_Handoff_Contract.json"
A1_DECISION = "POSTV16_AV3_A1_Decision_Contract.json"
A1_MANIFEST = "POSTV16_AV3_A1_Artifact_Manifest.csv"

A1_STATUS = (
    "AV3A1_COREY_RELPERM_PARAMETER_SUBSET_FIELD_MODEL_CORRELATION_BOUNDS_"
    "CHANNEL_SCHEMA_AND_SPLIT_REGISTRY_PROSPECTIVELY_FROZEN_NO_FIELD_GENERATION"
)

BASE_AV2 = Path("post_v16") / RID / "POSTV16_AV2_Variable_Porosity"
AV2A2_REL = BASE_AV2 / "POSTV16_AV2_A2_Porosity_Realization_and_Pore_Kinematics_Execution"
AV2A2_SUMMARY = "PAD_Stream_POSTV16_AV2_A2_Summary.json"
AV2A2_DECISION = "POSTV16_AV2_A2_Decision_Contract.json"
AV2A2_MANIFEST = "POSTV16_AV2_A2_Artifact_Manifest.csv"

AV2A2_STATUS = (
    "AV2A2_FROZEN_SPATIAL_POROSITY_REALIZATIONS_GENERATED_"
    "PRESSURE_Q_INVARIANCE_CERTIFIED_PORE_KINEMATICS_RECONSTRUCTED_PASS"
)

OUT_REL = BASE_AV3 / "POSTV16_AV3_A2_Corey_Relperm_Field_Realization_Certification_and_Streamline_Sampling"
FAIL_REL = BASE_AV3 / "POSTV16_AV3_A2_SCIENTIFIC_FAIL"
BLOCK_REL = BASE_AV3 / "POSTV16_AV3_A2_BLOCKED"

# --------------------------------------------------------------------------------------------------
# Frozen A1 design.
# --------------------------------------------------------------------------------------------------

GRID = (15, 50, 50)
NZ, NY, NX = GRID

DX_FT = 20.0
DY_FT = 20.0
DZ_FT = 4.0

FT_TO_M = 0.3048
DX_M = DX_FT * FT_TO_M
DY_M = DY_FT * FT_TO_M
DZ_M = DZ_FT * FT_TO_M

NSL = 1078
NN = 201

A_MAJOR_FT = 200.0
A_MINOR_FT = 200.0
A_VERT_FT = 15.0
AZIMUTH_DEG = 30.0

VARIABLE_PARAMETERS = ["nw", "no", "krw_max", "kro_max"]

TRANSFORMS = {
    "nw": {
        "center": 3.0,
        "half_range": 1.0,
        "scale": 2.0,
        "lower": 2.0,
        "upper": 4.0,
    },
    "no": {
        "center": 3.0,
        "half_range": 1.0,
        "scale": 2.0,
        "lower": 2.0,
        "upper": 4.0,
    },
    "krw_max": {
        "center": 0.80,
        "half_range": 0.20,
        "scale": 2.0,
        "lower": 0.60,
        "upper": 1.00,
    },
    "kro_max": {
        "center": 0.80,
        "half_range": 0.20,
        "scale": 2.0,
        "lower": 0.60,
        "upper": 1.00,
    },
}

FIXED_SWC = 0.20
FIXED_SOR = 0.20

TARGET_CORR = np.asarray(
    [
        [1.0, 0.5, 0.0, 0.0],
        [0.5, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.5],
        [0.0, 0.0, 0.5, 1.0],
    ],
    dtype=np.float64,
)

REALIZATIONS = [
    ("AV3CR0001", 260301, "AV2PHI0001", "TRAIN"),
    ("AV3CR0002", 260302, "AV2PHI0002", "TRAIN"),
    ("AV3CR0003", 260303, "AV2PHI0003", "VALIDATION"),
    ("AV3CR0004", 260304, "AV2PHI0004", "LOCKED_OOD_TEST"),
]

LATENT_ORTHO_TOL = 2.0e-12
LATENT_CORR_TOL = 2.0e-12
BOUNDS_TOL = 0.0


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
    rr = read_csv(directory / name)
    m = {r["file"]: r["sha256"] for r in rr}
    if not m:
        raise GateError("manifest_empty:" + name)
    for fn, expected in m.items():
        p = directory / fn
        if not p.is_file():
            raise GateError("manifest_missing:" + fn)
        if sha256_file(p) != expected:
            raise GateError("manifest_SHA:" + fn)
    return m


def json_bytes(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        return b""
    fields: list[str] = []
    for row in rows:
        for k in row:
            if k not in fields:
                fields.append(k)
    s = io.StringIO(newline="")
    w = csv.DictWriter(s, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return s.getvalue().encode()


def deterministic_npz_bytes(arrays: dict[str, Any]) -> bytes:
    outer = io.BytesIO()
    with zipfile.ZipFile(outer, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for key in sorted(arrays):
            b = io.BytesIO()
            np.save(b, np.asarray(arrays[key]), allow_pickle=False)
            info = zipfile.ZipInfo(f"{key}.npy", date_time=(1980, 1, 1, 0, 0, 0))
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


def standardize(x: np.ndarray) -> np.ndarray:
    a = np.asarray(x, dtype=np.float64)
    a = a - float(np.mean(a))
    s = float(np.std(a))
    if not np.isfinite(s) or s <= 0.0:
        raise ScientificFail("standardization_nonpositive_std", s)
    return a / s


def load_scalar_grid_csv(path: Path) -> np.ndarray:
    x = np.loadtxt(path, skiprows=1, dtype=np.float64)
    if x.size != NZ * NY * NX:
        raise GateError(f"grid_csv_cell_count:{path.name}:{x.size}")
    x = x.reshape(GRID, order="C")
    if not np.all(np.isfinite(x)):
        raise GateError("grid_csv_nonfinite:" + path.name)
    return x


def covariance_kernel() -> np.ndarray:
    az = np.deg2rad(AZIMUTH_DEG)

    iz = np.arange(NZ)
    iy = np.arange(NY)
    ix = np.arange(NX)

    z = np.minimum(iz, NZ - iz) * DZ_FT
    y = np.minimum(iy, NY - iy) * DY_FT
    x = np.minimum(ix, NX - ix) * DX_FT

    Z, Y, X = np.meshgrid(z, y, x, indexing="ij")

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
            "constitutive_residual_covariance_PSD",
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

    return standardize(R)


def orthogonalize_against(v: np.ndarray, basis: list[np.ndarray]) -> np.ndarray:
    shape = np.asarray(v).shape
    x = standardize(v).ravel()

    for b in basis:
        q = np.asarray(b, dtype=np.float64).ravel()
        denom = float(np.dot(q, q))
        if denom <= 0.0:
            raise ScientificFail("orthogonal_basis_zero_norm")
        x = x - float(np.dot(x, q) / denom) * q

    x = standardize(x).ravel()

    # A second modified-Gram-Schmidt pass suppresses finite-precision leakage.
    for b in basis:
        q = np.asarray(b, dtype=np.float64).ravel()
        x = x - float(np.dot(x, q) / np.dot(q, q)) * q

    x = standardize(x).ravel()
    return x.reshape(shape)


def reconstruct_phi_latent(phi: np.ndarray) -> np.ndarray:
    r = (np.asarray(phi, dtype=np.float64) - 0.20) / 0.10
    if not (float(np.min(r)) > -1.0 and float(np.max(r)) < 1.0):
        raise ScientificFail(
            "paired_AV2_phi_not_inside_inverse_transform_domain",
            [float(np.min(r)), float(np.max(r))],
        )
    g = 2.0 * np.arctanh(r)
    return standardize(g)


def build_geology_basis(z_k: np.ndarray, z_phi: np.ndarray) -> list[np.ndarray]:
    qk = standardize(z_k)
    qp = orthogonalize_against(z_phi, [qk])

    corr = float(np.corrcoef(qk.ravel(), qp.ravel())[0, 1])
    if abs(corr) > LATENT_ORTHO_TOL:
        raise ScientificFail("geology_basis_not_orthogonal", corr)

    return [qk, qp]


def build_constitutive_latents(
    z_k: np.ndarray,
    z_phi: np.ndarray,
    base_seed: int,
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    geology_basis = build_geology_basis(z_k, z_phi)

    residual_basis: list[np.ndarray] = []
    component_seeds = []

    for idx, name in enumerate(VARIABLE_PARAMETERS, start=1):
        seed = 10 * int(base_seed) + idx
        component_seeds.append(seed)

        raw = generate_standardized_residual(seed)
        q = orthogonalize_against(
            raw,
            geology_basis + residual_basis,
        )

        residual_basis.append(q)

    U = np.stack([q.ravel() for q in residual_basis], axis=0)

    gram = np.corrcoef(U)

    if float(np.max(np.abs(gram - np.eye(4)))) > LATENT_ORTHO_TOL:
        raise ScientificFail(
            "constitutive_residual_basis_not_orthonormal",
            float(np.max(np.abs(gram - np.eye(4)))),
        )

    L = np.linalg.cholesky(TARGET_CORR)
    G = L @ U

    # Every target latent remains standardized and orthogonal to the geology span.
    latents = {
        name: G[i].reshape(GRID)
        for i, name in enumerate(VARIABLE_PARAMETERS)
    }

    realized_corr = np.corrcoef(G)

    max_target_diff = float(np.max(np.abs(realized_corr - TARGET_CORR)))

    if max_target_diff > LATENT_CORR_TOL:
        raise ScientificFail(
            "target_latent_cross_correlation_mismatch",
            max_target_diff,
        )

    geology_corr = {}
    for name, g in latents.items():
        geology_corr[name] = {
            "corr_ZK": float(np.corrcoef(g.ravel(), z_k.ravel())[0, 1]),
            "corr_Zphi": float(np.corrcoef(g.ravel(), z_phi.ravel())[0, 1]),
        }

        if abs(geology_corr[name]["corr_ZK"]) > LATENT_ORTHO_TOL:
            raise ScientificFail(
                f"{name}_latent_not_orthogonal_to_ZK",
                geology_corr[name]["corr_ZK"],
            )

        if abs(geology_corr[name]["corr_Zphi"]) > LATENT_ORTHO_TOL:
            raise ScientificFail(
                f"{name}_latent_not_orthogonal_to_Zphi",
                geology_corr[name]["corr_Zphi"],
            )

    return latents, {
        "component_seeds": component_seeds,
        "residual_basis_corr": gram,
        "realized_latent_corr": realized_corr,
        "max_target_corr_difference": max_target_diff,
        "geology_corr": geology_corr,
    }


def transform_parameter(name: str, g: np.ndarray) -> np.ndarray:
    d = TRANSFORMS[name]
    return (
        d["center"]
        + d["half_range"]
        * np.tanh(np.asarray(g, dtype=np.float64) / d["scale"])
    )


def trilinear(
    field: np.ndarray,
    xyz_m: np.ndarray,
    dx: float,
    dy: float,
    dz: float,
    origin: np.ndarray,
):
    # Exact V16C2 sampling algebra, copied locally to avoid import side effects.
    nz, ny, nx = field.shape

    pts = xyz_m.reshape(-1, 3)

    fx = (pts[:, 0] - origin[0]) / dx
    fy = (pts[:, 1] - origin[1]) / dy
    fz = (pts[:, 2] - origin[2]) / dz

    fx_clip = np.clip(fx, 0.0, nx - 1.0)
    fy_clip = np.clip(fy, 0.0, ny - 1.0)
    fz_clip = np.clip(fz, 0.0, nz - 1.0)

    i0 = np.floor(fx_clip).astype(int)
    j0 = np.floor(fy_clip).astype(int)
    k0 = np.floor(fz_clip).astype(int)

    i1 = np.minimum(i0 + 1, nx - 1)
    j1 = np.minimum(j0 + 1, ny - 1)
    k1 = np.minimum(k0 + 1, nz - 1)

    wx = fx_clip - i0
    wy = fy_clip - j0
    wz = fz_clip - k0

    c000 = field[k0, j0, i0]
    c100 = field[k0, j0, i1]
    c010 = field[k0, j1, i0]
    c110 = field[k0, j1, i1]
    c001 = field[k1, j0, i0]
    c101 = field[k1, j0, i1]
    c011 = field[k1, j1, i0]
    c111 = field[k1, j1, i1]

    c00 = c000 * (1.0 - wx) + c100 * wx
    c10 = c010 * (1.0 - wx) + c110 * wx
    c01 = c001 * (1.0 - wx) + c101 * wx
    c11 = c011 * (1.0 - wx) + c111 * wx

    c0 = c00 * (1.0 - wy) + c10 * wy
    c1 = c01 * (1.0 - wy) + c11 * wy

    out = c0 * (1.0 - wz) + c1 * wz

    audit = {
        "x_clip_count": int(np.sum(fx != fx_clip)),
        "y_clip_count": int(np.sum(fy != fy_clip)),
        "z_clip_count": int(np.sum(fz != fz_clip)),
        "total_points": int(len(pts)),
    }

    return out.reshape(xyz_m.shape[:-1]), audit


def corr(a: np.ndarray, b: np.ndarray) -> float:
    return float(
        np.corrcoef(
            np.asarray(a, dtype=np.float64).ravel(),
            np.asarray(b, dtype=np.float64).ravel(),
        )[0, 1]
    )


def self_test() -> None:
    rng = np.random.default_rng(260399)

    z_k = standardize(rng.standard_normal((5, 8, 9)))
    z_phi_raw = 0.6 * z_k + math.sqrt(1.0 - 0.6**2) * standardize(
        rng.standard_normal((5, 8, 9))
    )
    z_phi = standardize(z_phi_raw)

    # Test generic Gram-Schmidt / target-correlation logic on synthetic vectors.
    basis = build_geology_basis(z_k, z_phi)

    residuals = []
    for _ in range(4):
        raw = rng.standard_normal((5, 8, 9))
        residuals.append(
            orthogonalize_against(raw, basis + residuals)
        )

    U = np.stack([x.ravel() for x in residuals])
    assert np.max(np.abs(np.corrcoef(U) - np.eye(4))) < 1.0e-12

    G = np.linalg.cholesky(TARGET_CORR) @ U
    assert np.max(np.abs(np.corrcoef(G) - TARGET_CORR)) < 1.0e-12

    for i, name in enumerate(VARIABLE_PARAMETERS):
        arr = transform_parameter(name, G[i].reshape((5, 8, 9)))
        d = TRANSFORMS[name]
        assert np.min(arr) > d["lower"]
        assert np.max(arr) < d["upper"]

    # Exact corrected exponent contract.
    assert TRANSFORMS["nw"]["lower"] == 2.0
    assert TRANSFORMS["nw"]["upper"] == 4.0
    assert TRANSFORMS["nw"]["center"] == 3.0
    assert TRANSFORMS["no"]["lower"] == 2.0
    assert TRANSFORMS["no"]["upper"] == 4.0
    assert TRANSFORMS["no"]["center"] == 3.0

    # Trilinear identity on a constant field.
    f = np.full((3, 4, 5), 7.25)
    xyz = np.asarray([[[0.0, 0.0, 0.0], [6.096, 6.096, 1.2192]]])
    out, audit = trilinear(f, xyz, 6.096, 6.096, 1.2192, np.zeros(3))
    assert np.allclose(out, 7.25)
    assert audit["total_points"] == 2

    print("POSTV16-AV3-A2 field-realization/sampling self-test: PASS")


def main(root: Path, drive: Path) -> int:
    gates: dict[str, dict[str, Any]] = {}
    stage = "preflight"

    field_generation_started = False
    completed_realizations = 0

    out = drive / OUT_REL
    failed = drive / FAIL_REL
    blocked = drive / BLOCK_REL

    diag_rows: list[dict[str, Any]] = []
    latent_rows: list[dict[str, Any]] = []
    physical_rows: list[dict[str, Any]] = []
    sampling_rows: list[dict[str, Any]] = []
    artifact_payloads: dict[str, bytes] = {}

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

    print("=" * 204)
    print("POSTV16-AV3-A2 — FROZEN COREY / RELPERM FIELD REALIZATION + CERTIFICATION + STREAMLINE SAMPLING")
    print("=" * 204)
    print("EXECUTION OF THE EXACT A1 FOUR-REALIZATION REGISTRY.")
    print("NO SEED PRETESTING. NO REJECTION. NO RESEEDING. NO POST-GENERATION RETUNING.")
    print("NO TRANSPORT Y TARGET GENERATION. NO TRAINING. NO INFERENCE.")
    print("NO PRESSURE RE-SOLVE. NO DARCY-Q RECOMPUTATION. NO POLLOCK RETRACE.")
    print("NO MAPBACK. NO LP. NO CMG.")
    print("Swc=Sor=0.20 AND AV2 LOCAL-PV CAPACITY SEMANTICS REMAIN FROZEN.")
    print()

    try:
        root = root.resolve()
        drive = drive.resolve()

        # ------------------------------------------------------------------------------------------
        # Repository authority.
        # ------------------------------------------------------------------------------------------
        stage = "repository_authority"

        parent = git_text(root, "rev-parse", "HEAD^")
        status = git_text(root, "status", "--porcelain")

        gate("repository_parent_is_AV3A1_commit", parent == PARENT_A1_COMMIT, parent)
        gate("repository_clean", status == "", repr(status))

        for fn, expected in SOURCE_BLOBS.items():
            p = root / fn
            actual = git_blob(p, root) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact", actual == expected, actual)

        # ------------------------------------------------------------------------------------------
        # Bind exact A1 PASS.
        # ------------------------------------------------------------------------------------------
        stage = "AV3A1_binding"

        a1 = drive / A1_REL
        gate("AV3A1_output_present", a1.is_dir(), str(a1))

        m1 = verify_manifest(a1, A1_MANIFEST)
        gate("AV3A1_manifest_SHA_closure", len(m1) == 9, len(m1))

        s1 = load_json(a1 / A1_SUMMARY)
        p1 = load_json(a1 / A1_PARAMETERS)
        f1 = load_json(a1 / A1_FIELD)
        c1 = load_json(a1 / A1_CHANNELS)
        sp1 = load_json(a1 / A1_SPLIT)
        h1 = load_json(a1 / A1_HANDOFF)
        d1 = load_json(a1 / A1_DECISION)
        r1 = read_csv(a1 / A1_REGISTRY)

        gate("AV3A1_status_exact", s1["status"] == A1_STATUS, s1["status"])
        gate("AV3A1_A2_authorized", d1["AV3_A2_authorized"] is True)
        gate("AV3A1_A2_next_id_exact", h1["milestone"] == "POSTV16-AV3-A2")
        gate("AV3A1_A2_execution_authorized", h1["execution"] is True)

        gate(
            "AV3A1_variable_parameter_subset_exact",
            p1["variable_parameters"] == VARIABLE_PARAMETERS,
            p1["variable_parameters"],
        )

        gate("AV3A1_swc_fixed", float(p1["fixed_parameters"]["swc"]) == FIXED_SWC)
        gate("AV3A1_sor_fixed", float(p1["fixed_parameters"]["sor"]) == FIXED_SOR)

        for name in VARIABLE_PARAMETERS:
            d = p1["parameter_transforms"][name]
            gate(
                f"AV3A1_{name}_transform_exact",
                float(d["center"]) == TRANSFORMS[name]["center"]
                and float(d["half_range"]) == TRANSFORMS[name]["half_range"]
                and float(d["latent_scale"]) == TRANSFORMS[name]["scale"]
                and float(d["open_lower_bound"]) == TRANSFORMS[name]["lower"]
                and float(d["open_upper_bound"]) == TRANSFORMS[name]["upper"],
                d,
            )

        frozen_corr = np.asarray(
            f1["latent_cross_parameter_correlation"]["matrix"],
            dtype=np.float64,
        )
        gate("AV3A1_target_corr_exact", np.array_equal(frozen_corr, TARGET_CORR))

        gate(
            "AV3A1_13_channel_schema",
            int(c1["AV3_total_channel_count"]) == 13,
            c1["AV3_total_channel_count"],
        )
        gate(
            "AV3A1_new_channels_exact",
            c1["new_AV3_channels_appended"]
            == ["nw_hat", "no_hat", "krw_max_hat", "kro_max_hat"],
        )

        frozen_registry = [
            (
                r["corey_realization_id"],
                int(r["base_seed"]),
                r["paired_porosity_realization_id"],
                r["partition"],
            )
            for r in r1
        ]
        gate("AV3A1_registry_exact", frozen_registry == REALIZATIONS, frozen_registry)

        gate(
            "AV3A1_locked_OOD_teacher_firewall",
            "no AV3 teacher target may be generated/opened"
            in sp1["AV3_locked_OOD_semantics"],
        )

        # ------------------------------------------------------------------------------------------
        # Bind exact frozen AV2 kinematics.
        # ------------------------------------------------------------------------------------------
        stage = "AV2A2_binding"

        av2a2 = drive / AV2A2_REL
        gate("AV2A2_output_present", av2a2.is_dir(), str(av2a2))

        m2 = verify_manifest(av2a2, AV2A2_MANIFEST)
        gate("AV2A2_manifest_SHA_closure", True, len(m2))

        s2 = load_json(av2a2 / AV2A2_SUMMARY)
        d2 = load_json(av2a2 / AV2A2_DECISION)

        gate("AV2A2_status_exact", s2["status"] == AV2A2_STATUS, s2["status"])
        gate("AV2A2_pressure_Q_invariance", d2["pressure_Q_invariance_certified"] is True)
        gate("AV2A2_Pollock_retraced_and_frozen", d2["Pollock_retraced"] is True)
        gate("AV2A2_TOF_recomputed_and_frozen", d2["TOF_recomputed"] is True)
        gate(
            "AV2A2_all_1078_streamlines",
            d2["all_1078_streamlines_captured_for_all_realizations"] is True,
        )

        # ------------------------------------------------------------------------------------------
        # Bind exact K latent and physical K field.
        # ------------------------------------------------------------------------------------------
        stage = "geology_anchor_binding"

        z_k = standardize(load_scalar_grid_csv(root / GAUSS))
        K = load_scalar_grid_csv(root / PERM)

        gate("ZK_shape_exact", z_k.shape == GRID, z_k.shape)
        gate("ZK_mean_zero", abs(float(np.mean(z_k))) <= 1.0e-12, float(np.mean(z_k)))
        gate("ZK_std_one", abs(float(np.std(z_k)) - 1.0) <= 1.0e-12, float(np.std(z_k)))
        gate("K_shape_exact", K.shape == GRID, K.shape)
        gate("K_positive", float(np.min(K)) > 0.0, float(np.min(K)))

        # ------------------------------------------------------------------------------------------
        # Execute the exact four-realization registry.
        # ------------------------------------------------------------------------------------------
        stage = "field_generation_and_sampling"
        field_generation_started = True

        for rid, base_seed, phi_rid, partition in REALIZATIONS:
            print()
            print("=" * 204)
            print(f"AV3-A2 REALIZATION — {rid} / {partition} / paired {phi_rid}")
            print("=" * 204)

            av2_npz = av2a2 / f"POSTV16_AV2_A2_{phi_rid}_Variable_Porosity_Pore_Kinematics.npz"
            sci_gate(f"{rid}_paired_AV2_artifact_present", av2_npz.is_file(), av2_npz.name)

            with np.load(av2_npz, allow_pickle=False) as z:
                required = {
                    "porosity",
                    "streamline_xyz_m",
                    "pollock_tof_s",
                    "streamline_weight_m3_s",
                }
                sci_gate(
                    f"{rid}_paired_AV2_required_arrays",
                    required.issubset(set(z.files)),
                    sorted(z.files),
                )

                phi = np.asarray(z["porosity"], dtype=np.float64)
                xyz = np.asarray(z["streamline_xyz_m"], dtype=np.float64)
                tof = np.asarray(z["pollock_tof_s"], dtype=np.float64)
                weight = np.asarray(z["streamline_weight_m3_s"], dtype=np.float64)

            sci_gate(f"{rid}_phi_shape", phi.shape == GRID, phi.shape)
            sci_gate(f"{rid}_XYZ_shape", xyz.shape == (NSL, NN, 3), xyz.shape)
            sci_gate(f"{rid}_TOF_shape", tof.shape == (NSL, NN), tof.shape)
            sci_gate(f"{rid}_weight_shape", weight.shape == (NSL,), weight.shape)
            sci_gate(
                f"{rid}_paired_arrays_finite",
                np.isfinite(phi).all()
                and np.isfinite(xyz).all()
                and np.isfinite(tof).all()
                and np.isfinite(weight).all(),
            )

            z_phi = reconstruct_phi_latent(phi)

            latents, audit = build_constitutive_latents(
                z_k=z_k,
                z_phi=z_phi,
                base_seed=base_seed,
            )

            fields = {
                name: transform_parameter(name, latents[name])
                for name in VARIABLE_PARAMETERS
            }

            sampled = {}
            sample_audits = {}

            for name in VARIABLE_PARAMETERS:
                arr = fields[name]
                d = TRANSFORMS[name]

                sci_gate(f"{rid}_{name}_shape", arr.shape == GRID, arr.shape)
                sci_gate(f"{rid}_{name}_finite", np.isfinite(arr).all())
                sci_gate(
                    f"{rid}_{name}_strict_open_bounds",
                    float(np.min(arr)) > d["lower"] + BOUNDS_TOL
                    and float(np.max(arr)) < d["upper"] - BOUNDS_TOL,
                    [float(np.min(arr)), float(np.max(arr))],
                )

                ss, sa = trilinear(
                    arr,
                    xyz,
                    DX_M,
                    DY_M,
                    DZ_M,
                    np.zeros(3, dtype=np.float64),
                )

                sci_gate(f"{rid}_{name}_sample_shape", ss.shape == (NSL, NN), ss.shape)
                sci_gate(f"{rid}_{name}_sample_finite", np.isfinite(ss).all())
                sci_gate(
                    f"{rid}_{name}_sample_bounds",
                    float(np.min(ss)) > d["lower"]
                    and float(np.max(ss)) < d["upper"],
                    [float(np.min(ss)), float(np.max(ss))],
                )

                sampled[name] = ss
                sample_audits[name] = sa

                sampling_rows.append({
                    "corey_realization_id": rid,
                    "paired_porosity_realization_id": phi_rid,
                    "partition": partition,
                    "parameter": name,
                    "method": "TRILINEAR_CELL_CENTERED_V16C2_EXACT_ALGEBRA",
                    **sa,
                    "sample_min": float(np.min(ss)),
                    "sample_mean": float(np.mean(ss)),
                    "sample_max": float(np.max(ss)),
                })

            # Latent-space certification rows.
            realized_corr = np.asarray(audit["realized_latent_corr"], dtype=np.float64)

            for i, name in enumerate(VARIABLE_PARAMETERS):
                latent_rows.append({
                    "corey_realization_id": rid,
                    "partition": partition,
                    "parameter": name,
                    "component_seed": int(audit["component_seeds"][i]),
                    "corr_ZK": float(audit["geology_corr"][name]["corr_ZK"]),
                    "corr_Zphi": float(audit["geology_corr"][name]["corr_Zphi"]),
                    "latent_mean": float(np.mean(latents[name])),
                    "latent_std": float(np.std(latents[name])),
                })

            # Physical-space outcomes. These are REPORT-ONLY, never retuned.
            for name in VARIABLE_PARAMETERS:
                physical_rows.append({
                    "corey_realization_id": rid,
                    "partition": partition,
                    "parameter_a": name,
                    "parameter_b": "K_MD",
                    "pearson_correlation": corr(fields[name], K),
                    "role": "REPORT_ONLY_NO_RETUNING",
                })
                physical_rows.append({
                    "corey_realization_id": rid,
                    "partition": partition,
                    "parameter_a": name,
                    "parameter_b": "porosity",
                    "pearson_correlation": corr(fields[name], phi),
                    "role": "REPORT_ONLY_NO_RETUNING",
                })

            for i in range(len(VARIABLE_PARAMETERS)):
                for j in range(i + 1, len(VARIABLE_PARAMETERS)):
                    a = VARIABLE_PARAMETERS[i]
                    b = VARIABLE_PARAMETERS[j]
                    physical_rows.append({
                        "corey_realization_id": rid,
                        "partition": partition,
                        "parameter_a": a,
                        "parameter_b": b,
                        "pearson_correlation": corr(fields[a], fields[b]),
                        "role": "REPORT_ONLY_NO_RETUNING",
                    })

            # Summary diagnostics.
            row = {
                "corey_realization_id": rid,
                "base_seed": base_seed,
                "paired_porosity_realization_id": phi_rid,
                "partition": partition,
                "latent_corr_max_abs_error": float(
                    np.max(np.abs(realized_corr - TARGET_CORR))
                ),
                "nw_min": float(np.min(fields["nw"])),
                "nw_mean": float(np.mean(fields["nw"])),
                "nw_max": float(np.max(fields["nw"])),
                "no_min": float(np.min(fields["no"])),
                "no_mean": float(np.mean(fields["no"])),
                "no_max": float(np.max(fields["no"])),
                "krw_max_min": float(np.min(fields["krw_max"])),
                "krw_max_mean": float(np.mean(fields["krw_max"])),
                "krw_max_max": float(np.max(fields["krw_max"])),
                "kro_max_min": float(np.min(fields["kro_max"])),
                "kro_max_mean": float(np.mean(fields["kro_max"])),
                "kro_max_max": float(np.max(fields["kro_max"])),
                "max_abs_latent_corr_to_ZK": max(
                    abs(float(audit["geology_corr"][name]["corr_ZK"]))
                    for name in VARIABLE_PARAMETERS
                ),
                "max_abs_latent_corr_to_Zphi": max(
                    abs(float(audit["geology_corr"][name]["corr_Zphi"]))
                    for name in VARIABLE_PARAMETERS
                ),
                "all_fields_certified": True,
            }
            diag_rows.append(row)

            npz_name = f"POSTV16_AV3_A2_{rid}_Corey_Relperm_Field_and_Streamline_Sampling.npz"

            artifact_payloads[npz_name] = deterministic_npz_bytes({
                "nw": fields["nw"],
                "no": fields["no"],
                "krw_max": fields["krw_max"],
                "kro_max": fields["kro_max"],
                "G_nw": latents["nw"],
                "G_no": latents["no"],
                "G_krw_max": latents["krw_max"],
                "G_kro_max": latents["kro_max"],
                "nw_streamline": sampled["nw"],
                "no_streamline": sampled["no"],
                "krw_max_streamline": sampled["krw_max"],
                "kro_max_streamline": sampled["kro_max"],
                "streamline_xyz_m": xyz,
                "pollock_tof_s": tof,
                "streamline_weight_m3_s": weight,
                "paired_porosity": phi,
                "corey_realization_id": np.asarray([rid], dtype="U32"),
                "paired_porosity_realization_id": np.asarray([phi_rid], dtype="U32"),
                "partition": np.asarray([partition], dtype="U32"),
                "base_seed": np.asarray([base_seed], dtype=np.int64),
                "component_seeds": np.asarray(audit["component_seeds"], dtype=np.int64),
                "target_latent_correlation": TARGET_CORR,
                "realized_latent_correlation": realized_corr,
                "Swc": np.asarray([FIXED_SWC], dtype=np.float64),
                "Sor": np.asarray([FIXED_SOR], dtype=np.float64),
            })

            completed_realizations += 1

        # ------------------------------------------------------------------------------------------
        # Final scientific closure.
        # ------------------------------------------------------------------------------------------
        stage = "scientific_closure"

        sci_gate(
            "exactly_four_realizations_completed",
            completed_realizations == 4,
            completed_realizations,
        )

        sci_gate(
            "all_realization_rows_certified",
            len(diag_rows) == 4
            and all(bool(r["all_fields_certified"]) for r in diag_rows),
        )

        sci_gate(
            "all_latent_target_correlations_within_tolerance",
            max(float(r["latent_corr_max_abs_error"]) for r in diag_rows)
            <= LATENT_CORR_TOL,
            max(float(r["latent_corr_max_abs_error"]) for r in diag_rows),
        )

        sci_gate(
            "all_latents_orthogonal_to_K_within_tolerance",
            max(float(r["max_abs_latent_corr_to_ZK"]) for r in diag_rows)
            <= LATENT_ORTHO_TOL,
            max(float(r["max_abs_latent_corr_to_ZK"]) for r in diag_rows),
        )

        sci_gate(
            "all_latents_orthogonal_to_phi_within_tolerance",
            max(float(r["max_abs_latent_corr_to_Zphi"]) for r in diag_rows)
            <= LATENT_ORTHO_TOL,
            max(float(r["max_abs_latent_corr_to_Zphi"]) for r in diag_rows),
        )

        sci_gate(
            "exactly_16_parameter_sampling_rows",
            len(sampling_rows) == 16,
            len(sampling_rows),
        )

        sci_gate(
            "all_sampling_points_accounted",
            all(int(r["total_points"]) == NSL * NN for r in sampling_rows),
        )

        # No transport targets/models have been created.
        gate("teacher_generation_false", True)
        gate("training_false", True)
        gate("inference_false", True)
        gate("pressure_resolve_false", True)
        gate("Darcy_Q_recompute_false", True)
        gate("Pollock_retrace_false", True)
        gate("mapback_false", True)
        gate("LP_execution_false", True)
        gate("CMG_false", True)

        next_contract = {
            "milestone": "POSTV16-AV3-A3",
            "name": (
                "Spatial Corey / Relative-Permeability Transport-Operator, "
                "Teacher/Dataset, Physics-Residual, and PI-RNN Protocol Freeze"
            ),
            "authorized": True,
            "execution": False,
            "required_decisions": [
                "define spatially varying effective-saturation/relperm evaluation on streamline nodes",
                "define conservative face treatment for spatially varying fractional-flow functions",
                "define spatially varying capillary-shape operator consistent with the A2 fields",
                "freeze AV3 train/validation teacher generation and locked-OOD leakage firewall",
                "freeze AV3 physics residual using the same constitutive fields as the teacher",
                "freeze 13-channel PI-RNN architecture/training protocol and checkpoint-selection rule",
                "do not generate AV3CR0004 transport targets before the AV3 checkpoint is frozen",
            ],
        }

        decision = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "protocol_id": PROTOCOL_ID,
            "realizations_completed": 4,
            "all_fields_inside_frozen_bounds": True,
            "latent_geology_orthogonality_certified": True,
            "latent_cross_parameter_correlation_certified": True,
            "physical_correlations_reported_without_retuning": True,
            "frozen_AV2_streamline_sampling_complete": True,
            "Swc": FIXED_SWC,
            "Sor": FIXED_SOR,
            "AV2_saturation_capacity_semantics_preserved": True,
            "pressure_Q_reused": True,
            "Pollock_TOF_reused": True,
            "R7D_graph_geometry_preserved": True,
            "teacher_generation_performed": False,
            "training_performed": False,
            "inference_performed": False,
            "pressure_resolve_performed": False,
            "Darcy_Q_recompute_performed": False,
            "Pollock_retrace_performed": False,
            "mapback_performed": False,
            "LP_execution_performed": False,
            "CMG_validation_performed": False,
            "AV3_A3_authorized": True,
            "next": next_contract,
        }

        summary = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "protocol_id": PROTOCOL_ID,
            "realizations_completed": 4,
            "variable_parameters": VARIABLE_PARAMETERS,
            "nw_open_bounds": [2.0, 4.0],
            "no_open_bounds": [2.0, 4.0],
            "krw_max_open_bounds": [0.60, 1.00],
            "kro_max_open_bounds": [0.60, 1.00],
            "fixed_Swc": FIXED_SWC,
            "fixed_Sor": FIXED_SOR,
            "streamlines_per_realization": NSL,
            "nodes_per_streamline": NN,
            "sampling_rows": len(sampling_rows),
            "teacher_generation": False,
            "training": False,
            "inference": False,
            "pressure_resolve": False,
            "Darcy_Q_recompute": False,
            "Pollock_retrace": False,
            "mapback": False,
            "LP_execution": False,
            "CMG_validation": False,
            "AV3_A3_authorized": True,
            "next": next_contract,
        }

        files = {
            "PAD_Stream_POSTV16_AV3_A2_Summary.json": json_bytes(summary),
            "POSTV16_AV3_A2_By_Realization_Diagnostics.csv": csv_bytes(diag_rows),
            "POSTV16_AV3_A2_Latent_Certification.csv": csv_bytes(latent_rows),
            "POSTV16_AV3_A2_Physical_Correlation_Outcomes.csv": csv_bytes(physical_rows),
            "POSTV16_AV3_A2_Streamline_Sampling_Audit.csv": csv_bytes(sampling_rows),
            "POSTV16_AV3_A2_Decision_Contract.json": json_bytes(decision),
            "POSTV16_AV3_A2_Final_Gate_Matrix.csv": csv_bytes(
                [{"gate": k, **v} for k, v in gates.items()]
            ),
            **artifact_payloads,
        }

        immutable_publish(out, files)

        manifest_rows = []
        for q in sorted(out.iterdir()):
            if q.is_file() and q.name != "POSTV16_AV3_A2_Artifact_Manifest.csv":
                manifest_rows.append({
                    "file": q.name,
                    "sha256": sha256_file(q),
                    "bytes": q.stat().st_size,
                })

        immutable_publish(
            out,
            {"POSTV16_AV3_A2_Artifact_Manifest.csv": csv_bytes(manifest_rows)},
        )

        print()
        print("=" * 204)
        print("POSTV16-AV3-A2: FULL FIELD-REALIZATION / CERTIFICATION / STREAMLINE-SAMPLING PASS")
        print("=" * 204)
        print("Frozen realizations completed                 : 4 / 4")
        print("Spatial variables                             : nw, no, krw_max, kro_max")
        print("nw / no open bounds                           : (2.0, 4.0)")
        print("krw_max / kro_max open bounds                 : (0.60, 1.00)")
        print("Swc / Sor                                     : 0.20 / 0.20 FIXED")
        print("Latent geology orthogonality                  : CERTIFIED")
        print("Latent target cross-correlation               : CERTIFIED")
        print("Physical correlations                         : REPORTED / NOT RETUNED")
        print("Streamline sampling                           : 4 x 1078 x 201")
        print("Pressure/Q                                    : REUSED / NOT RESOLVED")
        print("Pollock/TOF                                   : REUSED / NOT RETRACED")
        print("Teacher generation / training / inference     : False / False / False")
        print("POSTV16-AV3-A3                                : AUTHORIZED")
        print("AV3-A3 execution                              : NOT YET AUTHORIZED")
        print("=" * 204)

        return 0

    except ScientificFail as exc:
        failed.mkdir(parents=True, exist_ok=True)

        report = {
            "milestone": MILESTONE,
            "status": STATUS_FAIL,
            "failed_stage": stage,
            "failed_gate": exc.gate,
            "detail": exc.detail,
            "field_generation_started": field_generation_started,
            "completed_realizations": completed_realizations,
            "seed_rejection_authorized": False,
            "reseeding_authorized": False,
            "parameter_retuning_authorized": False,
            "teacher_generation_performed": False,
            "training_performed": False,
            "inference_performed": False,
            "AV3_A3_authorized": False,
            "gates": gates,
        }

        q = failed / "POSTV16_AV3_A2_Scientific_Fail_Report.json"

        if not q.exists():
            q.write_bytes(json_bytes(report))

        print()
        print("=" * 204)
        print("POSTV16-AV3-A2: SCIENTIFIC FAIL")
        print("=" * 204)
        print("Failed gate :", exc.gate)
        print("Detail      :", exc.detail)
        print("DO NOT REJECT OR RESEED THE REALIZATION.")
        print("DO NOT RETUNE THE FROZEN FIELD MODEL.")
        print("AV3-A3 NOT AUTHORIZED.")
        print("=" * 204)

        return 3

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)

        report = {
            "milestone": MILESTONE,
            "status": STATUS_BLOCKED,
            "failed_stage": stage,
            "exception": repr(exc),
            "field_generation_started": field_generation_started,
            "completed_realizations": completed_realizations,
            "teacher_generation_performed": False,
            "training_performed": False,
            "inference_performed": False,
            "AV3_A3_authorized": False,
            "gates": gates,
        }

        q = blocked / "POSTV16_AV3_A2_Blocked_Report.json"

        if not q.exists():
            q.write_bytes(json_bytes(report))

        print()
        print("=" * 204)
        print("POSTV16-AV3-A2: TECHNICAL BLOCK")
        print("=" * 204)
        print("Stage       :", stage)
        print("Exception   :", repr(exc))
        print("AV3-A3 NOT AUTHORIZED.")
        print("=" * 204)

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

    raise SystemExit(
        main(
            args.project_root,
            args.drive_root,
        )
    )
