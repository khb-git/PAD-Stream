#!/usr/bin/env python3
"""
PAD-Stream V16D-32
Control-Space 36-Case Stage-4 Learning Dataset Assembly
+ TRAIN-Only Normalization Contract

Scientific role
---------------
Assemble the predictor side of the new 36-case control-space learning dataset
without opening any LOCKED_OOD_TEST Stage-4 target array.

This milestone preserves the frozen C20 nine-channel interface:

    0 xi
    1 pollock_tau_hat
    2 adv_tau_hat
    3 log10_Kh
    4 log10_Kz_over_Kh
    5 porosity
    6 pressure_z
    7 target_time_hat
    8 target_eta_sequence

Raw slot 6 contains sampled pressure_psi. It becomes pressure_z only through
normalization statistics fit on TRAIN cases 0026-0027.

Partitions
----------
TRAIN           : geology0026 + geology0027 = 18 control cases
VALIDATION      : geology0028               =  9 control cases
LOCKED_OOD_TEST : geology0029               =  9 control cases

OOD firewall
------------
* OOD predictor X may be assembled and transformed with TRAIN-only statistics.
* OOD Y_transport arrays are NEVER np.load'ed here.
* OOD Y files are hash-bound only.
* No OOD predictor statistics are fit or reported.
* No training, tuning, model selection, or threshold design occurs here.
"""

from pathlib import Path
import hashlib
import json
import sys

import numpy as np


# =============================================================================
# ROOT / OUTPUT
# =============================================================================

R = Path(__file__).resolve().parent

OUT = (
    R
    / "output"
    / "V16_D32_CONTROLSPACE_36CASE_STAGE4_LEARNING_DATASET_TRAIN_ONLY_NORMALIZATION"
)
CASE_OUT = OUT / "cases"

OUT.mkdir(parents=True, exist_ok=True)
CASE_OUT.mkdir(parents=True, exist_ok=True)


# =============================================================================
# EXACT AUTHORITIES
# =============================================================================

# D31D: one-touch OOD evaluation contract frozen immediately before D32.
D31D_DIR = (
    R
    / "output"
    / "V16_D31D_FROZEN_ONE_TOUCH_FINAL_LOCKED_OOD_EVALUATION_CONTRACT"
)
D31D_CONTRACT = D31D_DIR / "V16D31D_OneTouch_Final_Locked_OOD_Evaluation_Contract.json"
D31D_SUMMARY = D31D_DIR / "PAD_Stream_V16D31D_Summary.json"

D31D_CONTRACT_SHA = (
    "7c664db19c041d3a611cbbc94de03a501a70f38922c62fd044cde1016d03228d"
)
D31D_SUMMARY_SHA = (
    "a98000f0456f2307fb2f5a6921b1975bdf462dfde43af5fa65de9e5474c676d3"
)

# Fresh Recipe1.1 geology authority: K + porosity.
D23_DIR = R / "output" / "V16_D23_FRESH_RECIPE1P1_GEOLOGIES_0026_0029"
D23_SUMMARY = D23_DIR / "PAD_Stream_V16D23_Summary.json"
D23_SUMMARY_SHA = (
    "ba96b21a0a33f5b2aae5e3ad408d11fbc0421e55770b233652c78d856fe19c98"
)

# 36-case conservative flow authority: directional K + pressure.
D25_DIR = R / "output" / "V16_D25_36CASE_CONTROLSPACE_SG2_SG3_SG4_FLOW_ENSEMBLE"
D25_CASES = D25_DIR / "cases"
D25_SUMMARY = D25_DIR / "PAD_Stream_V16D25_Summary.json"
D25_SUMMARY_SHA = (
    "55c5831bf0f0166355ec3542a221280bededf08004700ffedf13a7ae56538e45"
)

# 36-case Pollock 201-node coordinate authority.
D27_DIR = (
    R
    / "output"
    / "V16_D27_36CASE_SG6_STYLE_201NODE_POLLOCK_TRANSPORT_COORDINATES"
)
D27_CASES = D27_DIR / "cases"
D27_SUMMARY = D27_DIR / "PAD_Stream_V16D27_Summary.json"
D27_SUMMARY_SHA = (
    "6c10ede5895bed51a9324ff8503ec3dffbf8b3d908cc077bdfb476dc65a822f1"
)

# 36-case FMM/ADV hierarchy authority.
D29_DIR = (
    R
    / "output"
    / "V16_D29_R1_EXACT_D10C_DERIVED_FMM_ADV_36CASE_CONTROLSPACE_EXECUTION"
)
D29_CASES = D29_DIR / "cases"
D29_SUMMARY = D29_DIR / "PAD_Stream_V16D29_R1_Summary.json"
D29_SUMMARY_SHA = (
    "18c05132c5206431d2562cbf0341915ebba07bc79311e71ec129f5b84fc2788c"
)

# Stage-4 target partitions. D32 binds files/hashes but never opens OOD Y.
D31A_DIR = R / "output" / "V16_D31A_RESTARTABLE_TRAIN_18CASE_STAGE4_TRANSPORT"
D31A_CASES = D31A_DIR / "cases"
D31A_MANIFEST = D31A_DIR / "V16D31A_TRAIN_18Case_Manifest.json"
D31A_MANIFEST_SHA = (
    "b59d62bb839477b4158774c845b680b32a21543e9762645e95513f092992545b"
)

D31B_DIR = (
    R
    / "output"
    / "V16_D31B_R1_RESTARTABLE_VALIDATION_9CASE_STAGE4_TRANSPORT"
)
D31B_CASES = D31B_DIR / "cases"
D31B_MANIFEST = D31B_DIR / "V16D31B_R1_VALIDATION_9Case_Manifest.json"
D31B_MANIFEST_SHA = (
    "39adcee9baf710a3e9910a88b999a82aaf237d4601c995a387b040798e0fe163"
)

D31C_DIR = (
    R
    / "output"
    / "V16_D31C_R1_RESTARTABLE_LOCKED_OOD_9CASE_STAGE4_TRANSPORT"
)
D31C_CASES = D31C_DIR / "cases"
D31C_MANIFEST = D31C_DIR / "V16D31C_R1_LOCKED_OOD_9Case_Manifest.json"
D31C_MANIFEST_SHA = (
    "6e4fac63b6dcd8dad4e1675cd2d856811ffcf9231dadc50104349471da9df9a6"
)


# =============================================================================
# FROZEN EXPERIMENT / FEATURE CONTRACT
# =============================================================================

TRAIN_GEOLOGIES = ("0026", "0027")
VALIDATION_GEOLOGIES = ("0028",)
OOD_GEOLOGIES = ("0029",)

RATES_TPD = (350, 500, 650)
BHP_PSI = (1800, 2000, 2200)

DAYS = np.asarray(
    [30, 60, 100, 150, 250, 365, 500, 750, 1000],
    dtype=np.float64,
)

FEATURES = [
    "xi",
    "pollock_tau_hat",
    "adv_tau_hat",
    "log10_Kh",
    "log10_Kz_over_Kh",
    "porosity",
    "pressure_z",
    "target_time_hat",
    "target_eta_sequence",
]

# C20-compatible tensor shapes.
N_TIMES = 9
N_STREAMLINES = 1078
N_NODES = 201
N_FEATURES = 9

RAW_SHAPE = (N_TIMES, N_STREAMLINES, N_NODES, N_FEATURES)
TARGET_SHAPE = (N_TIMES, N_STREAMLINES, N_NODES)

# Frozen Cartesian geometry from the source-bound streamline sampling lineage.
NZ, NY, NX = 15, 50, 50
DX_M = 6.096
DY_M = 6.096
DZ_M = 1.2192

DOMAIN_MAX_M = np.asarray(
    [NX * DX_M, NY * DY_M, NZ * DZ_M],
    dtype=np.float64,
)

OUTSIDE_TOL_M = 1.0e-8


# =============================================================================
# HELPERS
# =============================================================================

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text())


def exact_sha(path: Path, expected: str) -> bool:
    return path.exists() and sha256(path) == expected


def partition_for_geology(geology: str) -> str:
    if geology in TRAIN_GEOLOGIES:
        return "TRAIN"
    if geology in VALIDATION_GEOLOGIES:
        return "VALIDATION"
    if geology in OOD_GEOLOGIES:
        return "LOCKED_OOD_TEST"
    raise RuntimeError(f"Unknown geology split: {geology}")


def case_id(geology: str, rate: int, bhp: int) -> str:
    return f"V16D_Foundation_Case_{geology}_R{rate}_B{bhp}"


def all_case_specs():
    return [
        (g, r, b)
        for g in (*TRAIN_GEOLOGIES, *VALIDATION_GEOLOGIES, *OOD_GEOLOGIES)
        for r in RATES_TPD
        for b in BHP_PSI
    ]


def exact_array(z, key: str, shape):
    if key not in z.files:
        raise RuntimeError(
            f"Required key '{key}' absent. Available keys: {list(z.files)}"
        )

    a = np.asarray(z[key])

    if a.shape != tuple(shape):
        raise RuntimeError(
            f"Key '{key}' expected shape {shape}, got {a.shape}"
        )

    if not np.issubdtype(a.dtype, np.number):
        raise RuntimeError(
            f"Key '{key}' is not numeric: dtype={a.dtype}"
        )

    a = np.asarray(a, dtype=np.float64)

    if not np.isfinite(a).all():
        raise RuntimeError(
            f"Key '{key}' contains non-finite values."
        )

    return a


def containing_cell_indices(xyz_m):
    """
    Contract-1.0 style containing-cell sample.
    No interpolation or numerical-closeness mapping.
    """
    xyz_m = np.asarray(xyz_m, dtype=np.float64)

    lo = xyz_m.min(axis=(0, 1))
    hi = xyz_m.max(axis=(0, 1))

    if (
        np.any(lo < -OUTSIDE_TOL_M)
        or np.any(hi > DOMAIN_MAX_M + OUTSIDE_TOL_M)
    ):
        raise RuntimeError(
            "Pollock XYZ outside frozen Cartesian domain: "
            f"min={lo}, max={hi}, domain_max={DOMAIN_MAX_M}"
        )

    i = np.clip(
        np.floor(xyz_m[..., 0] / DX_M).astype(np.int64),
        0,
        NX - 1,
    )
    j = np.clip(
        np.floor(xyz_m[..., 1] / DY_M).astype(np.int64),
        0,
        NY - 1,
    )
    k = np.clip(
        np.floor(xyz_m[..., 2] / DZ_M).astype(np.int64),
        0,
        NZ - 1,
    )

    return k, j, i


def unique_case_file(directory: Path, token: str, required_keys=()):
    """
    Resolve exactly one source artifact by exact case token + required schema.
    Never choose by numerical closeness.
    """
    hits = []

    for p in directory.glob("*.npz"):
        if token not in p.name:
            continue

        try:
            with np.load(p, allow_pickle=False) as z:
                if all(key in z.files for key in required_keys):
                    hits.append(p)
        except Exception:
            continue

    if len(hits) != 1:
        raise RuntimeError(
            f"{token}: expected exactly one artifact in {directory}, "
            f"found {len(hits)}: {[p.name for p in hits]}"
        )

    return hits[0]


def target_partition_paths(partition: str):
    if partition == "TRAIN":
        return D31A_CASES, D31A_MANIFEST
    if partition == "VALIDATION":
        return D31B_CASES, D31B_MANIFEST
    if partition == "LOCKED_OOD_TEST":
        return D31C_CASES, D31C_MANIFEST
    raise RuntimeError(partition)


def target_file_for(cid: str, partition: str) -> Path:
    case_dir, _ = target_partition_paths(partition)
    return case_dir / f"{cid}_Stage4_Transport.npz"


def build_manifest_artifact_sha_map():
    """
    Read only JSON sidecar manifests. No target np.load occurs.
    """
    out = {}

    for partition, manifest_path in [
        ("TRAIN", D31A_MANIFEST),
        ("VALIDATION", D31B_MANIFEST),
        ("LOCKED_OOD_TEST", D31C_MANIFEST),
    ]:
        m = read_json(manifest_path)

        for rec in m.get("cases", []):
            cid = rec.get("case_id")
            ah = rec.get("artifact_sha256")
            status = rec.get("status")
            part = rec.get("partition")

            if not cid or not ah:
                raise RuntimeError(
                    f"{partition} manifest record missing case_id/artifact SHA."
                )

            if status != "CERTIFIED":
                raise RuntimeError(
                    f"{cid}: target manifest status is not CERTIFIED."
                )

            if part != partition:
                raise RuntimeError(
                    f"{cid}: target manifest partition mismatch "
                    f"{part} != {partition}"
                )

            if cid in out:
                raise RuntimeError(
                    f"Duplicate target case identity across manifests: {cid}"
                )

            out[cid] = {
                "partition": partition,
                "artifact_sha256": ah,
            }

    return out


# =============================================================================
# CASE ASSEMBLY
# =============================================================================

def assemble_case_predictors(geology: str, rate: int, bhp: int):
    cid = case_id(geology, rate, bhp)
    partition = partition_for_geology(geology)

    # -------------------------------------------------------------------------
    # 1. Recipe1.1 geology: exact porosity authority.
    # -------------------------------------------------------------------------

    geology_path = D23_DIR / f"V16D_Geology_Case_{geology}_Recipe1p1.npz"

    if not geology_path.exists():
        raise RuntimeError(
            f"{cid}: missing Recipe1.1 geology artifact {geology_path}"
        )

    with np.load(geology_path, allow_pickle=False) as z:
        geo_Kx = exact_array(z, "Kx_mD", (NZ, NY, NX))
        geo_Ky = exact_array(z, "Ky_mD", (NZ, NY, NX))
        geo_Kz = exact_array(z, "Kz_mD", (NZ, NY, NX))
        porosity = exact_array(z, "porosity", (NZ, NY, NX))

    # -------------------------------------------------------------------------
    # 2. D25 exact flow case: directional permeability + pressure.
    # -------------------------------------------------------------------------

    flow_path = D25_CASES / f"{cid}_Flow.npz"

    if not flow_path.exists():
        raise RuntimeError(
            f"{cid}: missing D25 flow artifact {flow_path}"
        )

    with np.load(flow_path, allow_pickle=False) as z:
        Kx = exact_array(z, "Kx_mD", (NZ, NY, NX))
        Ky = exact_array(z, "Ky_mD", (NZ, NY, NX))
        Kz = exact_array(z, "Kz_mD", (NZ, NY, NX))
        pressure_psi = exact_array(z, "pressure_psi", (NZ, NY, NX))

        if "split" in z.files:
            split_value = str(np.asarray(z["split"]).item())
            if split_value != partition:
                raise RuntimeError(
                    f"{cid}: D25 split mismatch {split_value} != {partition}"
                )

    # Exact geology identity across D23 -> D25.
    if not np.array_equal(Kx, geo_Kx):
        raise RuntimeError(f"{cid}: D25 Kx differs from D23 geology authority.")
    if not np.array_equal(Ky, geo_Ky):
        raise RuntimeError(f"{cid}: D25 Ky differs from D23 geology authority.")
    if not np.array_equal(Kz, geo_Kz):
        raise RuntimeError(f"{cid}: D25 Kz differs from D23 geology authority.")

    # -------------------------------------------------------------------------
    # 3. D27 exact 201-node Pollock transport coordinates.
    # -------------------------------------------------------------------------

    d27_path = unique_case_file(
        D27_CASES,
        cid,
        required_keys=(
            "xi",
            "transport_xyz_m",
            "pollock_tau_s",
            "pollock_tau_end_s",
        ),
    )

    with np.load(d27_path, allow_pickle=False) as z:
        xi_1d = exact_array(z, "xi", (N_NODES,))
        xyz_m = exact_array(
            z,
            "transport_xyz_m",
            (N_STREAMLINES, N_NODES, 3),
        )
        pollock_tau_s = exact_array(
            z,
            "pollock_tau_s",
            (N_STREAMLINES, N_NODES),
        )
        tau_end_s = exact_array(
            z,
            "pollock_tau_end_s",
            (N_STREAMLINES,),
        )

    if not np.array_equal(
        xi_1d,
        np.linspace(0.0, 1.0, N_NODES),
    ):
        raise RuntimeError(f"{cid}: xi is not the frozen 201-node linspace.")

    if np.any(tau_end_s <= 0.0):
        raise RuntimeError(f"{cid}: nonpositive Pollock terminal TOF.")

    if not np.allclose(
        pollock_tau_s[:, -1],
        tau_end_s,
        rtol=1.0e-12,
        atol=1.0e-9,
    ):
        raise RuntimeError(f"{cid}: Pollock terminal TOF mismatch.")

    # -------------------------------------------------------------------------
    # 4. D29-R1 directional ADV grid sampled on exact Pollock locations.
    # -------------------------------------------------------------------------

    d29_path = unique_case_file(
        D29_CASES,
        cid,
        required_keys=("tau_adv_s",),
    )

    with np.load(d29_path, allow_pickle=False) as z:
        adv_grid_s = exact_array(
            z,
            "tau_adv_s",
            (NZ, NY, NX),
        )

    k, j, i = containing_cell_indices(xyz_m)

    adv_tau_s = adv_grid_s[k, j, i]

    # -------------------------------------------------------------------------
    # 5. Exact containing-cell sampling of geology / pressure.
    # -------------------------------------------------------------------------

    Kx_path = Kx[k, j, i]
    Ky_path = Ky[k, j, i]
    Kz_path = Kz[k, j, i]
    phi_path = porosity[k, j, i]
    pressure_path_psi = pressure_psi[k, j, i]

    Kh = np.sqrt(Kx_path * Ky_path)

    if np.any(Kh <= 0.0) or np.any(Kz_path <= 0.0):
        raise RuntimeError(
            f"{cid}: sampled permeability must be positive."
        )

    xi = np.broadcast_to(
        xi_1d[None, :],
        (N_STREAMLINES, N_NODES),
    )

    pollock_tau_hat = pollock_tau_s / tau_end_s[:, None]
    adv_tau_hat = adv_tau_s / tau_end_s[:, None]

    log10_Kh = np.log10(Kh)
    log10_Kz_over_Kh = np.log10(Kz_path / Kh)

    # -------------------------------------------------------------------------
    # 6. Nine frozen target times.
    # -------------------------------------------------------------------------
    #
    # IMPORTANT:
    # Raw feature slot 6 is pressure_psi. The feature is named pressure_z
    # because the immutable TRAIN-only transform later converts this slot to
    # its normalized form.
    # -------------------------------------------------------------------------

    X_raw = np.empty(RAW_SHAPE, dtype=np.float64)

    for ti, day in enumerate(DAYS):
        target_time_hat = np.full(
            (N_STREAMLINES, N_NODES),
            day / 1000.0,
            dtype=np.float64,
        )

        target_eta_sequence = np.broadcast_to(
            (86400.0 * day / tau_end_s)[:, None],
            (N_STREAMLINES, N_NODES),
        )

        X_raw[ti] = np.stack(
            [
                xi,
                pollock_tau_hat,
                adv_tau_hat,
                log10_Kh,
                log10_Kz_over_Kh,
                phi_path,
                pressure_path_psi,
                target_time_hat,
                target_eta_sequence,
            ],
            axis=-1,
        )

    if X_raw.shape != RAW_SHAPE:
        raise RuntimeError(
            f"{cid}: predictor shape mismatch {X_raw.shape}"
        )

    if not np.isfinite(X_raw).all():
        raise RuntimeError(
            f"{cid}: nonfinite raw predictor tensor."
        )

    meta = {
        "case_id": cid,
        "geology": geology,
        "injection_rate_tpd": rate,
        "producer_bhp_psi": bhp,
        "partition": partition,
        "shape": list(X_raw.shape),
        "feature_order": FEATURES,
        "control_encoding":
            "implicit through frozen flow/pressure/Pollock/ADV/eta fields; "
            "no direct rate/BHP channels added",
        "sampling":
            "containing Cartesian cell at each frozen Pollock XYZ node",
        "sources": {
            "D23_geology": {
                "path": str(geology_path.relative_to(R)),
                "sha256": sha256(geology_path),
                "keys": ["Kx_mD", "Ky_mD", "Kz_mD", "porosity"],
            },
            "D25_flow": {
                "path": str(flow_path.relative_to(R)),
                "sha256": sha256(flow_path),
                "keys": [
                    "Kx_mD",
                    "Ky_mD",
                    "Kz_mD",
                    "pressure_psi",
                ],
            },
            "D27_Pollock": {
                "path": str(d27_path.relative_to(R)),
                "sha256": sha256(d27_path),
                "keys": [
                    "xi",
                    "transport_xyz_m",
                    "pollock_tau_s",
                    "pollock_tau_end_s",
                ],
            },
            "D29_ADV": {
                "path": str(d29_path.relative_to(R)),
                "sha256": sha256(d29_path),
                "key": "tau_adv_s",
                "sampling_mode":
                    "frozen containing-cell sample at Pollock XYZ",
            },
        },
    }

    return X_raw, meta


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("=" * 78)
    print("PAD-Stream V16D-32")
    print(
        "Control-Space 36-Case Stage-4 Learning Dataset Assembly "
        "+ TRAIN-Only Normalization"
    )
    print("=" * 78)

    # -------------------------------------------------------------------------
    # 1. Provenance / firewall pre-gates
    # -------------------------------------------------------------------------

    gates = {
        "D31D_contract_SHA_exact":
            exact_sha(D31D_CONTRACT, D31D_CONTRACT_SHA),
        "D31D_summary_SHA_exact":
            exact_sha(D31D_SUMMARY, D31D_SUMMARY_SHA),

        "D23_summary_SHA_exact":
            exact_sha(D23_SUMMARY, D23_SUMMARY_SHA),
        "D25_summary_SHA_exact":
            exact_sha(D25_SUMMARY, D25_SUMMARY_SHA),
        "D27_summary_SHA_exact":
            exact_sha(D27_SUMMARY, D27_SUMMARY_SHA),
        "D29R1_summary_SHA_exact":
            exact_sha(D29_SUMMARY, D29_SUMMARY_SHA),

        "D31A_manifest_SHA_exact":
            exact_sha(D31A_MANIFEST, D31A_MANIFEST_SHA),
        "D31B_manifest_SHA_exact":
            exact_sha(D31B_MANIFEST, D31B_MANIFEST_SHA),
        "D31CR1_manifest_SHA_exact":
            exact_sha(D31C_MANIFEST, D31C_MANIFEST_SHA),
    }

    if D31D_SUMMARY.exists():
        d31d = read_json(D31D_SUMMARY)
        gates["D31D_status_authorizes_D32"] = (
            d31d.get("status")
            == "V16D_CONTROLSPACE_LOCKED_OOD_ONE_TOUCH_FINAL_EVALUATION_"
               "CONTRACT_FROZEN_OOD_REMAINS_SEALED_LEARNING_DATASET_"
               "ASSEMBLY_AUTHORIZED"
        )
        gates["D31D_OOD_not_opened"] = d31d.get("OOD_opened") is False
        gates["D31D_OOD_not_evaluated"] = d31d.get("OOD_evaluated") is False
    else:
        gates["D31D_status_authorizes_D32"] = False
        gates["D31D_OOD_not_opened"] = False
        gates["D31D_OOD_not_evaluated"] = False

    if D23_SUMMARY.exists():
        gates["D23_status_certified"] = (
            read_json(D23_SUMMARY).get("status")
            == "V16D_FRESH_RECIPE1P1_GEOLOGIES_0026_0029_GENERATED_"
               "CERTIFIED_36CASE_CONTROLSPACE_FLOW_GENERATION_AUTHORIZED"
        )
    else:
        gates["D23_status_certified"] = False

    if D25_SUMMARY.exists():
        gates["D25_status_certified"] = (
            read_json(D25_SUMMARY).get("status")
            == "V16D_36CASE_CONTROLSPACE_SG2_SG3_SG4_FLOW_ENSEMBLE_"
               "GENERATED_CERTIFIED_POLLOCK_EXPANSION_AUTHORIZED"
        )
    else:
        gates["D25_status_certified"] = False

    if D27_SUMMARY.exists():
        gates["D27_status_certified"] = (
            read_json(D27_SUMMARY).get("status")
            == "V16D_36CASE_201NODE_POLLOCK_TOF_TRANSPORT_COORDINATE_"
               "DATABASE_CERTIFIED_D9R1_METRIC_EXPANSION_AUTHORIZED"
        )
    else:
        gates["D27_status_certified"] = False

    if D29_SUMMARY.exists():
        gates["D29R1_status_certified"] = (
            read_json(D29_SUMMARY).get("status")
            == "V16D_36CASE_FMM_ADV_POLLOCK_TRAVELTIME_HIERARCHY_"
               "CERTIFIED_CONTROLSPACE_TRANSPORT_SUPERVISION_"
               "EXPANSION_AUTHORIZED"
        )
    else:
        gates["D29R1_status_certified"] = False

    print("\nPRE-GATES")
    for name, passed in gates.items():
        print("[PASS]" if passed else "[FAIL]", name)

    if not all(gates.values()):
        raise RuntimeError(
            "D32 blocked: frozen provenance/firewall pre-gate failed."
        )

    # -------------------------------------------------------------------------
    # 2. Exact case registry
    # -------------------------------------------------------------------------

    specs = all_case_specs()

    if len(specs) != 36:
        raise RuntimeError(f"Expected 36 cases, found {len(specs)}.")

    expected_counts = {
        "TRAIN": 18,
        "VALIDATION": 9,
        "LOCKED_OOD_TEST": 9,
    }

    actual_counts = {
        p: sum(partition_for_geology(g) == p for g, _, _ in specs)
        for p in expected_counts
    }

    if actual_counts != expected_counts:
        raise RuntimeError(
            f"Split mismatch: {actual_counts} != {expected_counts}"
        )

    target_hash_map = build_manifest_artifact_sha_map()

    expected_case_ids = [
        case_id(g, r, b)
        for g, r, b in specs
    ]

    if set(target_hash_map) != set(expected_case_ids):
        missing = sorted(set(expected_case_ids) - set(target_hash_map))
        extra = sorted(set(target_hash_map) - set(expected_case_ids))
        raise RuntimeError(
            f"Target registry mismatch. missing={missing}, extra={extra}"
        )

    # -------------------------------------------------------------------------
    # 3. Pass 1: assemble raw X + fit sufficient statistics on TRAIN ONLY
    # -------------------------------------------------------------------------

    accum = {
        f: {
            "n": 0,
            "sum": 0.0,
            "sumsq": 0.0,
            "min": np.inf,
            "max": -np.inf,
        }
        for f in FEATURES
    }

    case_records = []

    print("\nRAW PREDICTOR ASSEMBLY")
    print("  TRAIN statistics are accumulated only for geologies 0026-0027.")
    print("  VALIDATION/OOD are assembled but never contribute to normalization fit.")
    print("  No Y_transport array is opened.\n")

    for idx, (geology, rate, bhp) in enumerate(specs, 1):
        cid = case_id(geology, rate, bhp)
        partition = partition_for_geology(geology)

        print(
            f"[{idx:02d}/36] {cid}  partition={partition}"
        )

        X_raw, meta = assemble_case_predictors(
            geology,
            rate,
            bhp,
        )

        raw_path = CASE_OUT / f"{cid}_Predictors_RAW.npz"

        np.savez_compressed(
            raw_path,
            X_raw=X_raw,
            target_days=DAYS,
            feature_order=np.asarray(FEATURES, dtype="U64"),
            case_id=np.array(cid),
            partition=np.array(partition),
            geology=np.array(geology),
            injection_rate_tpd=np.array(rate),
            producer_bhp_psi=np.array(bhp),
        )

        meta["raw_artifact"] = str(raw_path.relative_to(R))
        meta["raw_sha256"] = sha256(raw_path)

        # TRAIN ONLY. Validation and OOD never enter the fit.
        if partition == "TRAIN":
            for channel, feature in enumerate(FEATURES):
                x = X_raw[..., channel]
                a = accum[feature]

                a["n"] += int(x.size)
                a["sum"] += float(
                    x.sum(dtype=np.float64)
                )
                a["sumsq"] += float(
                    np.square(
                        x,
                        dtype=np.float64,
                    ).sum(dtype=np.float64)
                )
                a["min"] = min(
                    a["min"],
                    float(x.min()),
                )
                a["max"] = max(
                    a["max"],
                    float(x.max()),
                )

        metadata_path = CASE_OUT / f"{cid}_RAW_Metadata.json"
        metadata_path.write_text(
            json.dumps(meta, indent=2)
        )

        case_records.append(meta)

    # -------------------------------------------------------------------------
    # 4. Freeze TRAIN-only normalization statistics
    # -------------------------------------------------------------------------

    stats = {}

    for feature, a in accum.items():
        if a["n"] <= 0:
            raise RuntimeError(
                f"No TRAIN samples accumulated for feature {feature}."
            )

        mean = a["sum"] / a["n"]
        variance = max(
            0.0,
            a["sumsq"] / a["n"] - mean * mean,
        )
        std = variance ** 0.5

        # Stable constant-channel classification.
        data_range = a["max"] - a["min"]
        scale = max(
            abs(a["max"]),
            abs(a["min"]),
            1.0,
        )
        effectively_constant = (
            data_range <= 1.0e-14 * scale
        )

        if effectively_constant:
            std = 0.0

        stats[feature] = {
            "n": a["n"],
            "mean": mean,
            "std": std,
            "min": a["min"],
            "max": a["max"],
            "policy":
                "CONSTANT_IDENTITY"
                if std == 0.0
                else "ZSCORE_TRAIN_ONLY",
        }

    stats_path = OUT / "V16D32_TRAIN_Only_Normalization_Statistics.json"

    stats_payload = {
        "milestone": "V16D-32",
        "fit_partition": "TRAIN_ONLY",
        "fit_geologies": list(TRAIN_GEOLOGIES),
        "fit_case_count": 18,
        "validation_policy": "TRANSFORM_ONLY",
        "locked_OOD_policy": "TRANSFORM_ONLY",
        "feature_order": FEATURES,
        "raw_pressure_semantics":
            "raw channel slot 6 = sampled pressure_psi; normalized slot = pressure_z",
        "target_used_for_statistics": False,
        "M_face_predictor": False,
        "direct_control_channels_added": False,
        "control_information":
            "encoded prospectively through pressure, Pollock/ADV travel time, "
            "and target_eta_sequence under each frozen rate/BHP case",
        "statistics": stats,
    }

    stats_path.write_text(
        json.dumps(stats_payload, indent=2)
    )

    # -------------------------------------------------------------------------
    # 5. Pass 2: immutable TRAIN transform applied to ALL partitions
    # -------------------------------------------------------------------------

    predictor_manifest_cases = []

    print("\nAPPLYING FROZEN TRAIN-ONLY TRANSFORM")

    for idx, (geology, rate, bhp) in enumerate(specs, 1):
        cid = case_id(geology, rate, bhp)
        partition = partition_for_geology(geology)

        raw_path = CASE_OUT / f"{cid}_Predictors_RAW.npz"

        with np.load(raw_path, allow_pickle=False) as z:
            X_raw = exact_array(
                z,
                "X_raw",
                RAW_SHAPE,
            )

        X = X_raw.copy()

        for channel, feature in enumerate(FEATURES):
            s = stats[feature]
            std = float(s["std"])

            if std > 0.0:
                X[..., channel] = (
                    X_raw[..., channel]
                    - float(s["mean"])
                ) / std

        if X.shape != RAW_SHAPE:
            raise RuntimeError(
                f"{cid}: normalized predictor shape mismatch."
            )

        if not np.isfinite(X).all():
            raise RuntimeError(
                f"{cid}: nonfinite normalized predictors."
            )

        norm_path = CASE_OUT / f"{cid}_Predictors_NORMALIZED.npz"

        np.savez_compressed(
            norm_path,
            X=X,
            target_days=DAYS,
            feature_order=np.asarray(FEATURES, dtype="U64"),
            case_id=np.array(cid),
            partition=np.array(partition),
            geology=np.array(geology),
            injection_rate_tpd=np.array(rate),
            producer_bhp_psi=np.array(bhp),
            normalization_statistics_sha256=np.array(
                sha256(stats_path)
            ),
        )

        target_path = target_file_for(
            cid,
            partition,
        )

        if not target_path.exists():
            raise RuntimeError(
                f"{cid}: target artifact absent: {target_path}"
            )

        expected_target_sha = target_hash_map[cid]["artifact_sha256"]
        actual_target_sha = sha256(target_path)

        if actual_target_sha != expected_target_sha:
            raise RuntimeError(
                f"{cid}: target SHA mismatch."
            )

        predictor_manifest_cases.append(
            {
                "case_id": cid,
                "geology": geology,
                "injection_rate_tpd": rate,
                "producer_bhp_psi": bhp,
                "partition": partition,

                "X_raw": {
                    "path": str(raw_path.relative_to(R)),
                    "sha256": sha256(raw_path),
                    "shape": list(RAW_SHAPE),
                },

                "X_normalized": {
                    "path": str(norm_path.relative_to(R)),
                    "sha256": sha256(norm_path),
                    "shape": list(RAW_SHAPE),
                },

                "Y_stage4": {
                    "path": str(target_path.relative_to(R)),
                    "sha256": actual_target_sha,
                    "shape_authority": list(TARGET_SHAPE),
                    "opened_in_D32": False,
                },
            }
        )

        print(
            f"[{idx:02d}/36] {cid} -> normalized SHA "
            f"{sha256(norm_path)[:16]}..."
        )

    # -------------------------------------------------------------------------
    # 6. Freeze predictor feature-order / sampling contract
    # -------------------------------------------------------------------------

    feature_contract = {
        "contract_id":
            "V16D_CONTROLSPACE_C20_9CHANNEL_PREDICTOR_CONTRACT_1.0",

        "milestone": "V16D-32",

        "feature_order": FEATURES,

        "shape_per_case": list(RAW_SHAPE),

        "sequence_axis":
            "201 frozen Pollock transport-coordinate nodes",

        "time_axis_days": DAYS.tolist(),

        "channel_semantics": {
            "xi":
                "frozen common 0-1 Pollock sequence coordinate",
            "pollock_tau_hat":
                "pollock_tau_s / pollock_tau_end_s",
            "adv_tau_hat":
                "D29-R1 directional ADV travel time sampled at each Pollock "
                "node by containing cell, divided by pollock_tau_end_s",
            "log10_Kh":
                "log10(sqrt(Kx*Ky)) sampled at each Pollock node",
            "log10_Kz_over_Kh":
                "log10(Kz/sqrt(Kx*Ky)) sampled at each Pollock node",
            "porosity":
                "D23 Recipe1.1 porosity sampled at each Pollock node",
            "pressure_z":
                "D25 pressure_psi sampled raw, then z-scored using TRAIN-only "
                "global channel statistics",
            "target_time_hat":
                "target_days / 1000",
            "target_eta_sequence":
                "86400 * target_days / pollock_tau_end_s, broadcast over nodes",
        },

        "sampling_contract": {
            "grid_shape_zyx": [15, 50, 50],
            "cell_size_m_xyz": [DX_M, DY_M, DZ_M],
            "rule":
                "containing Cartesian cell at exact frozen Pollock XYZ; "
                "no interpolation",
            "boundary_policy":
                "floor coordinate/cell-size then clip to valid final cell index; "
                "outside-domain tolerance 1e-8 m",
        },

        "control_encoding": {
            "direct_rate_channel": False,
            "direct_BHP_channel": False,
            "rule":
                "rate/BHP act through the already-frozen physical case state: "
                "pressure, Pollock/ADV travel times, and eta; no new Stage-4 "
                "control law or direct channel is invented",
        },

        "physics_hierarchy": {
            "Pollock": "AUTHORITATIVE_KINEMATICS",
            "ADV": "AUXILIARY_DIRECTIONAL_PREDICTOR",
            "FMM": "NOT_IN_C20_9CHANNEL_PREDICTOR",
            "M_face": "PHYSICS_SIDECAR_NOT_PREDICTOR",
        },

        "normalization": {
            "fit": "TRAIN_ONLY",
            "validation": "TRANSFORM_ONLY",
            "locked_OOD": "TRANSFORM_ONLY",
            "statistics_file": str(stats_path.relative_to(R)),
            "statistics_sha256": sha256(stats_path),
        },

        "prohibited": [
            "validation normalization fitting",
            "OOD normalization fitting",
            "Y target use for predictor statistics",
            "M_face predictor insertion",
            "direct rate/BHP channel insertion without a new prospective contract",
            "case selection",
            "streamline selection",
            "OOD adaptation",
            "model training in D32",
            "model selection in D32",
        ],
    }

    feature_contract_path = (
        OUT
        / "V16D32_ControlSpace_C20_9Channel_Predictor_Contract.json"
    )

    feature_contract_path.write_text(
        json.dumps(feature_contract, indent=2)
    )

    # -------------------------------------------------------------------------
    # 7. Freeze 36-case predictor manifest
    # -------------------------------------------------------------------------

    predictor_manifest_path = (
        OUT
        / "V16D32_36Case_Predictor_Manifest.json"
    )

    predictor_manifest = {
        "milestone": "V16D-32",
        "status": "FROZEN",
        "split": {
            "TRAIN": [
                x["case_id"]
                for x in predictor_manifest_cases
                if x["partition"] == "TRAIN"
            ],
            "VALIDATION": [
                x["case_id"]
                for x in predictor_manifest_cases
                if x["partition"] == "VALIDATION"
            ],
            "LOCKED_OOD_TEST": [
                x["case_id"]
                for x in predictor_manifest_cases
                if x["partition"] == "LOCKED_OOD_TEST"
            ],
        },
        "feature_order": FEATURES,
        "normalization_statistics_sha256":
            sha256(stats_path),
        "feature_contract_sha256":
            sha256(feature_contract_path),
        "cases": predictor_manifest_cases,
    }

    predictor_manifest_path.write_text(
        json.dumps(predictor_manifest, indent=2)
    )

    # -------------------------------------------------------------------------
    # 8. Freeze learning dataset registry
    # -------------------------------------------------------------------------

    dataset_registry_path = (
        OUT
        / "V16D32_Frozen_36Case_Learning_Dataset_Registry.json"
    )

    dataset_registry = {
        "name":
            "V16D_CONTROLSPACE_STAGE4_LEARNING_DATASET_1.0",

        "generalization_unit":
            "COMPLETE_FOUNDATION_CASE",

        "cases": predictor_manifest_cases,

        "split_counts": expected_counts,

        "geology_split": {
            "TRAIN": list(TRAIN_GEOLOGIES),
            "VALIDATION": list(VALIDATION_GEOLOGIES),
            "LOCKED_OOD_TEST": list(OOD_GEOLOGIES),
        },

        "controls": {
            "injection_rate_tpd": list(RATES_TPD),
            "producer_bhp_psi": list(BHP_PSI),
            "complete_factorial_per_geology": True,
        },

        "target_days": DAYS.tolist(),

        "predictor_shape_per_case": list(RAW_SHAPE),
        "target_shape_per_case": list(TARGET_SHAPE),

        "feature_order": FEATURES,

        "normalization": {
            "fit_partition": "TRAIN_ONLY",
            "statistics_path": str(stats_path.relative_to(R)),
            "statistics_sha256": sha256(stats_path),
            "validation": "TRANSFORM_ONLY",
            "locked_OOD": "TRANSFORM_ONLY",
        },

        "target_access_in_D32": {
            "TRAIN_Y_np_load": False,
            "VALIDATION_Y_np_load": False,
            "LOCKED_OOD_Y_np_load": False,
            "target_binding_method":
                "manifest-record SHA + direct file SHA only",
        },

        "locked_OOD": {
            "geology": "0029",
            "manifest_sha256": D31C_MANIFEST_SHA,
            "one_touch_contract_sha256": D31D_CONTRACT_SHA,
            "opened": False,
            "evaluated": False,
        },
    }

    dataset_registry_path.write_text(
        json.dumps(dataset_registry, indent=2)
    )

    # -------------------------------------------------------------------------
    # 9. Final gates
    # -------------------------------------------------------------------------

    split_counts_from_manifest = {
        p: sum(
            x["partition"] == p
            for x in predictor_manifest_cases
        )
        for p in expected_counts
    }

    final_gates = dict(gates)

    final_gates.update(
        {
            "exactly_36_predictor_cases":
                len(predictor_manifest_cases) == 36,

            "split_counts_18_9_9":
                split_counts_from_manifest == expected_counts,

            "all_9_controls_each_geology":
                all(
                    sum(
                        x["geology"] == geology
                        for x in predictor_manifest_cases
                    ) == 9
                    for geology in (
                        *TRAIN_GEOLOGIES,
                        *VALIDATION_GEOLOGIES,
                        *OOD_GEOLOGIES,
                    )
                ),

            "feature_order_exact_C20_9channel":
                FEATURES == [
                    "xi",
                    "pollock_tau_hat",
                    "adv_tau_hat",
                    "log10_Kh",
                    "log10_Kz_over_Kh",
                    "porosity",
                    "pressure_z",
                    "target_time_hat",
                    "target_eta_sequence",
                ],

            "all_X_shapes_exact":
                all(
                    x["X_raw"]["shape"] == list(RAW_SHAPE)
                    and x["X_normalized"]["shape"] == list(RAW_SHAPE)
                    for x in predictor_manifest_cases
                ),

            "all_Y_shape_authorities_exact":
                all(
                    x["Y_stage4"]["shape_authority"] == list(TARGET_SHAPE)
                    for x in predictor_manifest_cases
                ),

            "all_target_SHA_verified_without_np_load": True,

            "TRAIN_only_normalization_fit": True,
            "VALIDATION_transform_only": True,
            "LOCKED_OOD_transform_only": True,

            "no_validation_statistics_fit": True,
            "no_OOD_statistics_fit": True,
            "no_OOD_predictor_aggregate_report": True,

            "no_Y_array_opened_in_D32": True,
            "no_LOCKED_OOD_Y_np_load": True,

            "Pollock_primary": True,
            "ADV_auxiliary": True,
            "FMM_not_predictor": True,
            "M_face_not_predictor": True,

            "no_direct_control_channels": True,
            "controls_enter_through_frozen_physics": True,

            "no_training": True,
            "no_model_selection": True,
            "no_tuning": True,
            "OOD_remains_sealed": True,
        }
    )

    ok = bool(all(final_gates.values()))

    status = (
        "V16D_CONTROLSPACE_36CASE_C20_PREDICTOR_DATASET_ASSEMBLED_"
        "TRAIN_ONLY_NORMALIZATION_FROZEN_OOD_REMAINS_SEALED_"
        "TRAINING_PROTOCOL_FREEZE_AUTHORIZED"
        if ok
        else "V16D_D32_CONTROLSPACE_LEARNING_DATASET_BLOCKED"
    )

    next_milestone = (
        "V16D-33 — Control-space recurrent Stage-4 model architecture, "
        "training, validation-selection, and checkpoint protocol freeze"
        if ok
        else "Repair D32 predictor/source/normalization gate; keep OOD sealed."
    )

    summary_path = OUT / "PAD_Stream_V16D32_Summary.json"

    summary = {
        "milestone": "V16D-32",
        "status": status,
        "predictor_cases": len(predictor_manifest_cases),
        "split_counts": split_counts_from_manifest,
        "feature_order": FEATURES,
        "normalization_statistics_sha256":
            sha256(stats_path),
        "feature_contract_sha256":
            sha256(feature_contract_path),
        "predictor_manifest_sha256":
            sha256(predictor_manifest_path),
        "dataset_registry_sha256":
            sha256(dataset_registry_path),
        "D31D_contract_sha256":
            D31D_CONTRACT_SHA,
        "OOD_opened": False,
        "OOD_evaluated": False,
        "model_trained": False,
        "gates": final_gates,
        "next_milestone": next_milestone,
    }

    summary_path.write_text(
        json.dumps(summary, indent=2)
    )

    print("\nTRAIN-ONLY NORMALIZATION STATISTICS")
    for feature in FEATURES:
        s = stats[feature]
        print(
            f"  {feature:24s} "
            f"mean={s['mean']:.9e} "
            f"std={s['std']:.9e} "
            f"min={s['min']:.9e} "
            f"max={s['max']:.9e} "
            f"{s['policy']}"
        )

    print("\nFINAL GATES")
    for name, passed in final_gates.items():
        print("[PASS]" if passed else "[FAIL]", name)

    print("\nSTATUS")
    print(" ", status)

    print("\nLOCKED-OOD STATUS")
    print(
        "  SEALED — geology0029 predictors transformed with TRAIN-only stats; "
        "no OOD Y array opened."
    )

    print("\nARTIFACT HASHES")
    print("  Normalization :", sha256(stats_path))
    print("  Feature contract:", sha256(feature_contract_path))
    print("  Predictor manifest:", sha256(predictor_manifest_path))
    print("  Dataset registry:", sha256(dataset_registry_path))
    print("  Summary:", sha256(summary_path))

    print("\nNEXT")
    print(" ", next_milestone)

    if not ok:
        sys.exit(2)


if __name__ == "__main__":
    main()
