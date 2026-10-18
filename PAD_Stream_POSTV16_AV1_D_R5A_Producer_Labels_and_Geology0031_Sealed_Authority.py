#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import pickle
from pathlib import Path
import subprocess
import sys
import zipfile
from typing import Any

import numpy as np


MILESTONE = "POSTV16-AV1-D-R5A"
STATUS_PASS = (
    "AV1DR5A_DERIVED_V16_PRODUCER_LABELS_CERTIFIED_AND_"
    "GEOLOGY0031_SOURCE_AUTHENTIC_ACCEPTANCE_AUTHORITY_GENERATED_SHA_SEALED"
)
STATUS_BLOCKED = "AV1DR5A_LABEL_OR_GEOLOGY0031_AUTHORITY_GENERATION_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT_R5_COMMIT = "6c764af030a0f9cfce889db870e706ce8f3dd5cf"

R5 = "PAD_Stream_POSTV16_AV1_D_R5_Prospective_Producer_Resolved_Repair_and_Geology0031_Freeze.py"
R5_BLOB = "c5d2f64f124153b4e352f302302e0558a31c5c58"

R3A = "PAD_Stream_POSTV16_AV1_D_R3A_Generate_and_Seal_Geology0030_Acceptance_Authority.py"
R3A_BLOB = "8a12228f488394e24fdf11479e335f245c800478"

D23 = "PAD_Stream_V16D23_Generate_and_Certify_Fresh_Recipe1p1_Geologies_0026_0029.py"
D23_BLOB = "e4c9fa6988040b6a2034717b12ea1831eb345e95"

D25 = "PAD_Stream_V16D25_D7B_Derived_36Case_ControlSpace_SG2_SG3_SG4_Flow_Ensemble_Execution.py"
D25_BLOB = "ba71dae06d2ef665eaafee4d0f4095fdcb2277e0"

SG2 = "PAD_Stream_V15SG2_Anisotropic_Transmissibility.py"
SG2_BLOB = "7242012d3e758472abc3ee7f543831b92d2cf419"

SG3 = "PAD_Stream_V15SG3_FiveSpot_Pressure_Solve.py"
SG3_BLOB = "66a379cd97ee9120f69e7e7e949171541e4918c3"

SG4 = "PAD_Stream_V15SG4_Conservative_Darcy_Fluxes.py"
SG4_BLOB = "8d49f88bdf55b0da087af2bed04e69967740e695"

SG5 = "PAD_Stream_V15SG5_Exact_Pollock_Streamlines.py"
SG5_BLOB = "9a0b64ea7e669904d0d9855ade1c6b052f05ecea"

D28R1 = "PAD_Stream_V16D28_R1_Exact_D9R1_36Case_Conservative_Face_Metric_Expansion.py"
D28R1_BLOB = "39cd0290055fe5c563a8c8908d30bce9260ee549"

C17 = "PAD_Stream_V16C17_Production_Source_Authentic_Y_Transport_Tensor_Generation_and_Certification.py"
C17_BLOB = "310e10853ce6f160ee8c9bd270f2823893bf98d3"

SOURCE_BLOBS = {
    R5: R5_BLOB,
    R3A: R3A_BLOB,
    D23: D23_BLOB,
    D25: D25_BLOB,
    SG2: SG2_BLOB,
    SG3: SG3_BLOB,
    SG4: SG4_BLOB,
    SG5: SG5_BLOB,
    D28R1: D28R1_BLOB,
    C17: C17_BLOB,
}

C14_CONTRACT = (
    Path("output")
    / "V16_C14_PRODUCTION_FULL_PHYSICS_TRANSPORT_PARAMETER_AUTHORITY_CONTRACT"
    / "V16C14_Production_Full_Physics_Parameter_Contract.json"
)
C14_CONTRACT_BLOB = "552c77ab01c362cb904383cbcccfb4be96a1d097"

C15_CONTRACT = (
    Path("output")
    / "V16_C15_PRODUCTION_PHYSICAL_TARGET_TIME_SCHEDULE_AUTHORITY_CONTRACT"
    / "V16C15_Production_Target_Time_Schedule_Contract.json"
)
C15_CONTRACT_BLOB = "5a4c38cc130be67bf56fb29eebe19a4eeb1852dd"

R5_OUT_REL = (
    Path("post_v16")
    / RID
    / "POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"
    / "POSTV16_AV1_D_R5_Prospective_Producer_Resolved_Repair_and_Geology0031_Freeze"
)
R5_SUMMARY = "PAD_Stream_POSTV16_AV1_D_R5_Summary.json"
R5_CONNECTIVITY = "POSTV16_AV1_D_R5_Derived_V16_Producer_Connectivity_Contract.json"
R5_REPAIR = "POSTV16_AV1_D_R5_Producer_Resolved_Repair_Protocol.json"
R5_ACCEPT = "POSTV16_AV1_D_R5_Geology0031_Independent_Acceptance_Authority.json"
R5_MANIFEST = "POSTV16_AV1_D_R5_Artifact_Manifest.csv"
R5_STATUS = (
    "AV1DR5_PRODUCER_RESOLVED_REPAIR_AND_GEOLOGY0031_INDEPENDENT_"
    "ACCEPTANCE_PROTOCOL_PROSPECTIVELY_FROZEN"
)

OUT_REL = (
    Path("post_v16")
    / RID
    / "POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"
    / "POSTV16_AV1_D_R5A_Producer_Labels_and_Geology0031_Sealed_Authority"
)
BLOCKED_REL = (
    Path("post_v16")
    / RID
    / "POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"
    / "POSTV16_AV1_D_R5A_BLOCKED"
)

FOUNDATION_NAME = "V16A_Foundation_Case_0001.npz"
FOUNDATION_SHA = "4239e412ca6e2780f108c8eb1b0252e80a56be305bce48cc58e50d6140b86acc"

C2_NAME = "V16C2_Multi_Coordinate_Streamline_Transport_Database.npz"
C2_SHA = "f5fe7bd2bcb113374b32966911d50976f8a581f95e63e2dd0e94642caa6f11b6"

C18R_NAME = "V16C18R_Certified_Conditioning_to_Y_Transport_Dataset.npz"
C18R_SHA = "1b610ad3c90aa827be4c466ed71f3a3b771d0498bd915395096efda057f445f3"

GEOLOGY_ID = "0031"
GEOLOGY_SEED = 390051
RATE_TPD = 500.0
BHP_PSI = 2000.0
CASE_ID = "POSTV16_AV1_Geology0031_R500_B2000"

EXPECTED_GRID = (15, 50, 50)
EXPECTED_STREAMLINES = 1078
EXPECTED_NODES = 201
EXPECTED_FACES = 200
EXPECTED_Y_SHAPE = (9, 1078, 201)
EXPECTED_SAMPLES = 9702

SECONDS_PER_DAY = 86400.0
CFL = 0.25
EPS = 1.0e-12
TARGET_DAYS_EXPECTED = [30.0, 60.0, 100.0, 150.0, 250.0, 365.0, 500.0, 750.0, 1000.0]

CONNECTIVITY_RULE_ID = "POSTV16_DERIVED_V16_TERMINAL_XY_NEAREST_PRODUCER_COLUMN_V1"
DX_M = 6.096
DY_M = 6.096
PRODUCERS = {
    "PROD_SW": (4.0, 4.0),
    "PROD_SE": (45.0, 4.0),
    "PROD_NW": (4.0, 45.0),
    "PROD_NE": (45.0, 45.0),
}
PRODUCER_ORDER = ["PROD_SW", "PROD_SE", "PROD_NW", "PROD_NE"]


class GateError(RuntimeError):
    pass


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
    return s.getvalue().encode("utf-8")


def json_bytes(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


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


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError(f"cannot_load_module:{path}")
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def verify_manifest(directory: Path, manifest_name: str) -> dict[str, str]:
    rows = read_csv(directory / manifest_name)
    m = {r["file"]: r["sha256"] for r in rows}
    for name, expected in m.items():
        p = directory / name
        if not p.is_file():
            raise GateError(f"manifest_file_missing:{name}")
        actual = sha256_file(p)
        if actual != expected:
            raise GateError(f"manifest_SHA_mismatch:{name}:{actual}:{expected}")
    return m


def find_named_exact(roots: list[Path], name: str, expected_sha: str) -> Path:
    matches: list[Path] = []
    for rr in roots:
        if not rr.exists():
            continue
        for p in rr.rglob(name):
            try:
                if p.is_file() and sha256_file(p) == expected_sha:
                    matches.append(p.resolve())
            except OSError:
                pass
    if not matches:
        raise GateError(f"exact_authority_not_found:{name}:{expected_sha}")
    uniq = sorted(set(matches), key=lambda p: (len(str(p)), str(p)))
    return uniq[0]


def valok(v: Any) -> bool:
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    if isinstance(v, dict):
        vals = [x for x in v.values() if isinstance(x, (bool, np.bool_))]
        return all(bool(x) for x in vals) if vals else True
    return True


def extract_well_source(sg4: Any, k_mD: np.ndarray, pressure_psi: np.ndarray) -> np.ndarray:
    ew = sg4.construct_expected_well_rates(k_mD, pressure_psi)
    ws = None
    if isinstance(ew, np.ndarray):
        ws = np.asarray(ew, dtype=float)
    elif isinstance(ew, tuple):
        for x in ew:
            if isinstance(x, np.ndarray) and x.shape == EXPECTED_GRID:
                ws = np.asarray(x, dtype=float)
                break
    elif isinstance(ew, dict):
        for key in ("well_source", "source", "q_well"):
            if key in ew:
                ws = np.asarray(ew[key], dtype=float)
                break
    if ws is None:
        raise GateError("could_not_bind_SG4_well_source")
    return ws


def derive_producer_labels(xyz: np.ndarray):
    endpoint = np.asarray(xyz[:, -1, :], dtype=np.float64)
    ii = endpoint[:, 0] / DX_M
    jj = endpoint[:, 1] / DY_M
    wells = np.asarray([PRODUCERS[n] for n in PRODUCER_ORDER], dtype=np.float64)
    dist2 = (
        (ii[:, None] - wells[None, :, 0]) ** 2
        + (jj[:, None] - wells[None, :, 1]) ** 2
    )
    min_dist = np.min(dist2, axis=1)
    tie_count = np.sum(dist2 == min_dist[:, None], axis=1)
    arg = np.argmin(dist2, axis=1)
    labels = np.asarray([PRODUCER_ORDER[int(x)] for x in arg], dtype="U16")
    return endpoint, ii, jj, dist2, min_dist, tie_count, arg, labels


def self_test() -> None:
    if GEOLOGY_SEED != 160400 + (31 - 2) * 7919:
        raise RuntimeError("seed_formula")
    test = np.zeros((4, 201, 3), dtype=float)
    for k, name in enumerate(PRODUCER_ORDER):
        i, j = PRODUCERS[name]
        test[k, -1, 0] = i * DX_M
        test[k, -1, 1] = j * DY_M
    _, _, _, _, _, ties, _, labels = derive_producer_labels(test)
    if not np.all(ties == 1):
        raise RuntimeError("tie_logic")
    if labels.tolist() != PRODUCER_ORDER:
        raise RuntimeError("label_logic")
    b = deterministic_npz_bytes({"a": np.arange(4), "b": labels})
    if not b.startswith(b"PK"):
        raise RuntimeError("deterministic_npz")
    print("POSTV16-AV1-D-R5A self-test: PASS")


def main(root: Path, drive: Path) -> int:
    gates: dict[str, dict[str, Any]] = {}
    stage = "preflight"
    out = drive / OUT_REL
    blocked = drive / BLOCKED_REL

    def gate(name: str, passed: Any, value: Any = None) -> None:
        ok = bool(passed)
        gates[name] = {"passed": ok, "value": value}
        suffix = f" — {value}" if value is not None else ""
        print(f"[{'PASS' if ok else 'FAIL'}] {name}{suffix}")
        if not ok:
            raise GateError(name)

    print("=" * 176)
    print("POSTV16-AV1-D-R5A — CERTIFY DERIVED PRODUCER LABELS + GENERATE/SHA-SEAL GEOLOGY0031")
    print("=" * 176)
    print("NO MODEL INFERENCE. NO REPAIR TRAINING. NO CHECKPOINT LOADING.")
    print("TRAINING-SIDE LABELS ARE NEW DERIVED V16 METADATA, NOT HISTORICAL V15 producer_id.")
    print("ACCEPTANCE-SIDE GEOLOGY0031 USES SOURCE-AUTHENTIC SG5/D28 PRODUCER LABELS.")
    print("GEOLOGY0031 STAGE4 TARGET IS GENERATED AND SEALED BUT NOT OPENED FOR MODEL EVALUATION.\n")

    try:
        root = root.resolve()
        drive = drive.resolve()

        head = git_text(root, "rev-parse", "HEAD")
        parent = git_text(root, "rev-parse", "HEAD^")
        status = git_text(root, "status", "--porcelain")

        gate("repository_parent_is_R5_commit", parent == PARENT_R5_COMMIT, parent)
        gate("repository_clean", status == "", repr(status))

        for fname, blob in SOURCE_BLOBS.items():
            p = root / fname
            actual = git_blob_sha(p, root) if p.is_file() else "missing"
            gate(f"{Path(fname).stem}_git_blob_exact", actual == blob, actual)

        for p, blob, label in (
            (root / C14_CONTRACT, C14_CONTRACT_BLOB, "C14_contract"),
            (root / C15_CONTRACT, C15_CONTRACT_BLOB, "C15_contract"),
        ):
            actual = git_blob_sha(p, root) if p.is_file() else "missing"
            gate(f"{label}_git_blob_exact", actual == blob, actual)

        stage = "R5_freeze_binding"

        r5 = drive / R5_OUT_REL
        gate("R5_output_present", r5.is_dir(), str(r5))
        r5_manifest = verify_manifest(r5, R5_MANIFEST)
        gate("R5_manifest_SHA_closure", True, len(r5_manifest))

        r5s = load_json(r5 / R5_SUMMARY)
        conn = load_json(r5 / R5_CONNECTIVITY)
        repair = load_json(r5 / R5_REPAIR)
        accept = load_json(r5 / R5_ACCEPT)

        gate("R5_status_exact", r5s["status"] == R5_STATUS, r5s["status"])
        gate("R5_training_false", r5s["training_performed"] is False)
        gate("R5_inference_false", r5s["model_inference_performed"] is False)
        gate("R5_geology0031_not_generated", r5s["geology0031_generated"] is False)
        gate("R5_connectivity_rule_exact", conn["rule_id"] == CONNECTIVITY_RULE_ID, conn["rule_id"])
        gate("R5_historical_V15_label_claim_false", conn["historical_V15_producer_id_claim"] is False)
        gate("R5_connectivity_not_predictor_feature", conn["training_role"].startswith("grouping/weighting"))
        gate("R5_repair_single_candidate", repair["single_candidate_policy"]["candidate_count"] == 1)
        gate("R5_repair_threshold_not_training", repair["new_repair_term"]["acceptance_threshold_used"] is False)
        gate("R5_geology0030_prohibited_from_training", repair["training_data"]["geology0030_role"].startswith("diagnostic historical evidence only"))
        gate("R5_acceptance_geology0031", accept["geology_id"] == GEOLOGY_ID, accept["geology_id"])
        gate("R5_acceptance_seed390051", int(accept["seed"]) == GEOLOGY_SEED, accept["seed"])
        gate("R5_reference_controls_exact", float(accept["controls"]["CO2_injection_tonnes_per_day"]) == RATE_TPD and float(accept["controls"]["producer_BHP_psi"]) == BHP_PSI)
        gate("R5_target_must_seal_before_training", accept["generation_order"]["seal_target_before_R5_repair_training"] is True)
        gate("R5_target_prohibited_training_selection", accept["generation_order"]["target_may_not_be_opened_for_training_or_selection"] is True)

        stage = "exact_training_authority_discovery"

        foundation = find_named_exact([root, drive], FOUNDATION_NAME, FOUNDATION_SHA)
        c2 = find_named_exact([root, drive], C2_NAME, C2_SHA)
        c18r = find_named_exact([root, drive], C18R_NAME, C18R_SHA)

        gate("Foundation_exact_SHA", sha256_file(foundation) == FOUNDATION_SHA, str(foundation))
        gate("C2_exact_SHA", sha256_file(c2) == C2_SHA, str(c2))
        gate("C18R_exact_SHA", sha256_file(c18r) == C18R_SHA, str(c18r))

        stage = "derived_V16_producer_label_certification"

        with np.load(foundation, allow_pickle=False) as z:
            f_xyz = np.asarray(z["streamline_xyz"], dtype=np.float64)
        with np.load(c2, allow_pickle=False) as z:
            c2_xyz = np.asarray(z["streamline_xyz_m"], dtype=np.float64)
        with np.load(c18r, allow_pickle=False) as z:
            c18_streamline_index = np.asarray(z["streamline_index"], dtype=np.int64)
            c18_time_index = np.asarray(z["time_index"], dtype=np.int64)

        gate("Foundation_XYZ_shape_exact", f_xyz.shape == (EXPECTED_STREAMLINES, EXPECTED_NODES, 3), f_xyz.shape)
        gate("C2_XYZ_shape_exact", c2_xyz.shape == f_xyz.shape, c2_xyz.shape)
        xyz_linf = float(np.max(np.abs(f_xyz - c2_xyz)))
        gate("Foundation_C2_streamline_order_geometry_identity", xyz_linf <= 1.0e-12, xyz_linf)

        expected_si = np.tile(np.arange(EXPECTED_STREAMLINES, dtype=np.int64), 9)
        expected_ti = np.repeat(np.arange(9, dtype=np.int64), EXPECTED_STREAMLINES)
        gate("C18R_sample_count_exact", c18_streamline_index.shape == (EXPECTED_SAMPLES,), c18_streamline_index.shape)
        gate("C18R_time_major_streamline_index_exact", np.array_equal(c18_streamline_index, expected_si))
        gate("C18R_time_index_exact", np.array_equal(c18_time_index, expected_ti))

        endpoint, ii, jj, dist2, min_dist2, tie_count, label_code, labels = derive_producer_labels(f_xyz)

        gate("derived_labels_shape_exact", labels.shape == (EXPECTED_STREAMLINES,), labels.shape)
        gate("derived_labels_no_exact_ties", np.all(tie_count == 1), int(np.sum(tie_count != 1)))
        unique, counts = np.unique(labels, return_counts=True)
        label_counts = {str(k): int(v) for k, v in zip(unique, counts)}
        gate("derived_labels_all_four_producers_present", set(unique.tolist()) == set(PRODUCER_ORDER), label_counts)
        gate("derived_labels_all_1078_assigned", int(sum(label_counts.values())) == EXPECTED_STREAMLINES, label_counts)

        sample_labels = labels[c18_streamline_index]
        gate("derived_sample_labels_shape_exact", sample_labels.shape == (EXPECTED_SAMPLES,), sample_labels.shape)
        gate("derived_labels_repeat_exact_across_nine_times", all(np.array_equal(sample_labels[t*EXPECTED_STREAMLINES:(t+1)*EXPECTED_STREAMLINES], labels) for t in range(9)))

        label_bytes = deterministic_npz_bytes({
            "producer_label": labels,
            "producer_code": label_code.astype(np.int64),
            "producer_order": np.asarray(PRODUCER_ORDER, dtype="U16"),
            "terminal_xyz_m": endpoint,
            "terminal_i_continuous": ii,
            "terminal_j_continuous": jj,
            "distance2_to_producer_columns": dist2,
            "minimum_distance2": min_dist2,
            "tie_count": tie_count.astype(np.int64),
            "streamline_index": np.arange(EXPECTED_STREAMLINES, dtype=np.int64),
            "rule_id": np.array(CONNECTIVITY_RULE_ID),
            "historical_V15_producer_id_claim": np.array(False),
        })

        label_cert = {
            "milestone": MILESTONE,
            "status": "CERTIFIED",
            "rule_id": CONNECTIVITY_RULE_ID,
            "authority_class": "NEW_POST_FREEZE_DERIVED_V16_CONNECTIVITY_METADATA",
            "historical_V15_producer_id_claim": False,
            "Foundation_sha256": FOUNDATION_SHA,
            "C2_sha256": C2_SHA,
            "C18R_sha256": C18R_SHA,
            "Foundation_C2_XYZ_Linf_m": xyz_linf,
            "streamlines": EXPECTED_STREAMLINES,
            "producer_counts": label_counts,
            "no_exact_ties": True,
            "all_four_producers_present": True,
            "training_alignment": "streamline_index 0..1077 repeated in exact C18R time-major order",
            "predictor_feature": False,
            "Pollock_retrace": False,
            "geology0030_information_used": False,
        }

        stage = "load_physics_sources"

        d23 = load_module(root / D23, "postv16_r5a_d23")
        sg2 = load_module(root / SG2, "postv16_r5a_sg2")
        sg3 = load_module(root / SG3, "postv16_r5a_sg3")
        sg4 = load_module(root / SG4, "postv16_r5a_sg4")
        sg5 = load_module(root / SG5, "postv16_r5a_sg5")
        d28 = load_module(root / D28R1, "postv16_r5a_d28")
        c17 = load_module(root / C17, "postv16_r5a_c17")

        gate("SG3_reference_rate_exact", float(sg3.CO2_MASS_RATE_TONNES_DAY) == RATE_TPD, float(sg3.CO2_MASS_RATE_TONNES_DAY))
        gate("SG3_reference_BHP_exact", float(sg3.PRODUCER_BHP_PSI) == BHP_PSI, float(sg3.PRODUCER_BHP_PSI))
        gate("SG4_reference_rate_exact", float(sg4.CO2_MASS_RATE_TONNES_DAY) == RATE_TPD, float(sg4.CO2_MASS_RATE_TONNES_DAY))
        gate("SG4_reference_BHP_exact", float(sg4.PRODUCER_BHP_PSI) == BHP_PSI, float(sg4.PRODUCER_BHP_PSI))

        stage = "geology0031_generation"

        G, K, eig_min, raw_mean, raw_std = d23.generate(GEOLOGY_SEED)
        G = np.asarray(G, dtype=np.float64)
        K = np.asarray(K, dtype=np.float64)
        Kx = K.copy()
        Ky = K.copy()
        Kz = 0.1 * K
        phi = np.full_like(K, 0.2)

        geology_gates = {
            "shape_exact": G.shape == EXPECTED_GRID,
            "finite": bool(np.isfinite(G).all() and np.isfinite(K).all()),
            "sample_mean_exact": abs(float(np.mean(G))) < 1.0e-12,
            "sample_std_exact": abs(float(np.std(G)) - 1.0) < 1.0e-12,
            "K_strictly_inside_50_1000_mD": float(np.min(K)) > 50.0 and float(np.max(K)) < 1000.0,
            "Kx_eq_Ky": bool(np.array_equal(Kx, Ky)),
            "Kz_eq_0p1Kh": bool(np.allclose(Kz, 0.1 * Kx, rtol=0.0, atol=1.0e-12)),
            "porosity_0p2": bool(np.array_equal(phi, np.full_like(phi, 0.2))),
            "spectral_psd": float(eig_min) >= -1.0e-10,
        }
        for k, v in geology_gates.items():
            gate(f"geology0031_{k}", v)

        geology_bytes = deterministic_npz_bytes({
            "G_standardized": G,
            "Kx_mD": Kx,
            "Ky_mD": Ky,
            "Kz_mD": Kz,
            "porosity": phi,
            "geology_case_id": np.array(GEOLOGY_ID),
            "seed": np.array(GEOLOGY_SEED, dtype=np.int64),
        })

        stage = "reference_flow_generation"

        kx, ky, kz = sg2.build_directional_permeability(K)
        kfx, kfy, kfz = sg2.build_face_permeabilities(kx, ky, kz)
        sg2.build_transmissibilities(kfx, kfy, kfz)

        tx, ty, tz = sg3.construct_si_transmissibilities(kfx, kfy, kfz)
        assembled = sg3.assemble_pressure_system(K, tx, ty, tz)
        A, b = assembled[:2]
        solved = sg3.solve_pressure(A, b)
        p = np.asarray(solved[0] if isinstance(solved, tuple) else solved, dtype=float)
        if p.size == int(np.prod(EXPECTED_GRID)):
            p = p.reshape(EXPECTED_GRID)
        ppsi = p / sg3.PSI_TO_PA if np.nanmedian(p) > 1.0e5 else p

        flux = sg4.compute_face_fluxes(ppsi, tx, ty, tz)
        qx, qy, qz = [np.asarray(x, dtype=float) for x in flux[:3]]
        div = np.asarray(sg4.compute_flux_divergence(qx, qy, qz), dtype=float)
        well_source = extract_well_source(sg4, K, ppsi)
        residual = div - well_source

        finite_flow = all(np.isfinite(x).all() for x in (ppsi, qx, qy, qz, div, well_source))
        local = float(np.linalg.norm(residual.ravel()) / max(np.linalg.norm(well_source.ravel()), 1.0e-30))
        gross = float(np.abs(well_source).sum())
        inj = float(well_source[well_source > 0.0].sum())
        prod = float(-well_source[well_source < 0.0].sum())
        throughput = max(abs(inj), abs(prod), 1.0e-30)
        global_gross = float(abs(residual.sum()) / max(gross, 1.0e-30))
        global_throughput = float(abs(residual.sum()) / throughput)
        well_balance = float(abs(inj - prod) / throughput)

        gate("reference_flow_finite", finite_flow)
        gate("reference_flow_local_relative_L2", local <= 1.0e-9, local)
        gate("reference_flow_global_gross_scaled", global_gross <= 1.0e-9, global_gross)
        gate("reference_flow_global_throughput_scaled", global_throughput <= 1.0e-9, global_throughput)
        gate("reference_flow_well_balance_relative", well_balance <= 1.0e-9, well_balance)

        flow_bytes = deterministic_npz_bytes({
            "Kx_mD": np.asarray(kx),
            "Ky_mD": np.asarray(ky),
            "Kz_mD": np.asarray(kz),
            "kfx_mD": np.asarray(kfx),
            "kfy_mD": np.asarray(kfy),
            "kfz_mD": np.asarray(kfz),
            "Tx_SI": np.asarray(tx),
            "Ty_SI": np.asarray(ty),
            "Tz_SI": np.asarray(tz),
            "pressure_psi": ppsi,
            "Qx": qx,
            "Qy": qy,
            "Qz": qz,
            "divergence": div,
            "well_source": well_source,
            "geology_case_id": np.array(GEOLOGY_ID),
            "foundation_case_id": np.array(CASE_ID),
            "partition": np.array("LOCKED_INDEPENDENT_ACCEPTANCE"),
            "geology_seed": np.array(GEOLOGY_SEED, dtype=np.int64),
            "injection_tonnes_day": np.array(RATE_TPD),
            "producer_BHP_psi": np.array(BHP_PSI),
        })

        stage = "Pollock_generation"

        vel = sg5.construct_face_pore_velocities(qx, qy, qz)
        gate("SG5_velocity_return_contract", isinstance(vel, tuple) and len(vel) >= 3)
        vx, vy, vz = vel[:3]

        built = sg5.build_seeds(qx, qy, qz)
        gate("SG5_seed_return_contract", isinstance(built, tuple) and len(built) == 2)
        faces, seeds = built
        streamlines = sg5.trace_streamlines(seeds, vx, vy, vz)
        validation = sg5.validate_streamlines(faces, seeds, streamlines)

        gate("SG5_source_validation_pass", valok(validation))
        gate("SG5_exact_1078_seeds", len(seeds) == EXPECTED_STREAMLINES, len(seeds))
        gate("SG5_exact_1078_streamlines", len(streamlines) == EXPECTED_STREAMLINES, len(streamlines))
        gate("SG5_one_streamline_per_seed", len(streamlines) == len(seeds))

        pollock_payload = {
            "foundation_case_id": CASE_ID,
            "split": "LOCKED_INDEPENDENT_ACCEPTANCE",
            "faces": faces,
            "seeds": seeds,
            "streamlines": streamlines,
            "validation": validation,
        }
        pollock_bytes = pickle.dumps(pollock_payload, protocol=pickle.HIGHEST_PROTOCOL)

        stage = "D28_D9R1_metric_generation"

        n = len(streamlines)
        xyz = np.empty((n, EXPECTED_NODES, 3), dtype=float)
        tau = np.empty((n, EXPECTED_NODES), dtype=float)
        arc = np.empty((n, EXPECTED_NODES), dtype=float)
        xd = np.empty((n, EXPECTED_NODES), dtype=float)
        mf = np.empty((n, EXPECTED_FACES), dtype=float)
        mn = np.empty((n, EXPECTED_NODES), dtype=float)
        invf = np.empty((n, EXPECTED_FACES), dtype=float)
        te = np.empty(n, dtype=float)
        plen = np.empty(n, dtype=float)
        weight = np.empty(n, dtype=float)
        producer = np.empty(n, dtype="U32")
        sl_status = np.empty(n, dtype="U32")
        seed_id = np.empty(n, dtype=np.int64)

        for i, sl in enumerate(streamlines):
            q = d28.one(sl)
            (
                xyz[i],
                tau[i],
                arc[i],
                xd[i],
                mf[i],
                mn[i],
                invf[i],
                te[i],
                plen[i],
                weight[i],
                producer[i],
                sl_status[i],
                seed_id[i],
            ) = q

        reciprocal = float(np.max(np.abs(1.0 / mf - invf)))
        metric_gates = {
            "1078_streamlines": n == EXPECTED_STREAMLINES,
            "201_nodes": xyz.shape == (EXPECTED_STREAMLINES, EXPECTED_NODES, 3),
            "200_faces": mf.shape == (EXPECTED_STREAMLINES, EXPECTED_FACES),
            "finite": bool(all(np.isfinite(a).all() for a in (xyz, tau, arc, xd, mf, mn, invf, te, plen, weight))),
            "positive_TOF": bool(np.all(te > 0.0)),
            "positive_weight": bool(np.all(weight > 0.0)),
            "positive_path": bool(np.all(plen > 0.0)),
            "theta_TOF_monotone": bool(np.all(np.diff(tau, axis=1) > 0.0)),
            "xD_monotone": bool(np.all(np.diff(xd, axis=1) > 0.0)),
            "M_face_positive": bool(np.all(mf > 0.0)),
            "M_node_sidecar_positive": bool(np.all(mn > 0.0)),
            "reciprocal_identity": reciprocal < 1.0e-12,
            "producer_status_all": bool(np.all(sl_status == "PRODUCER")),
            "four_producers": len(set(producer.tolist())) == 4,
        }
        for k, v in metric_gates.items():
            gate(f"metric_{k}", v)

        theta = np.linspace(0.0, 1.0, EXPECTED_NODES)
        metric_bytes = deterministic_npz_bytes({
            "foundation_case_id": np.array(CASE_ID),
            "partition": np.array("LOCKED_INDEPENDENT_ACCEPTANCE"),
            "theta": theta,
            "xyz_m": xyz,
            "pollock_tau_s": tau,
            "pollock_tau_end_s": te,
            "arc_length_m": arc,
            "path_length_m": plen,
            "xD": xd,
            "M_face_dtheta_dxD": mf,
            "M_node_sidecar_dtheta_dxD": mn,
            "dxD_dtheta_face": invf,
            "streamline_weight_m3_s": weight,
            "producer": producer,
            "status": sl_status,
            "seed_id": seed_id,
            "c7_contract": np.array("M_face=Delta(theta)/Delta(xD); node M is sidecar only"),
        })

        stage = "C17_Stage4_target_generation"

        pc = load_json(root / C14_CONTRACT)
        tc = load_json(root / C15_CONTRACT)
        production_parameters = pc["production_parameters"]

        def value(key: str) -> float:
            return float(production_parameters[key]["value"])

        par = {
            k: value(src)
            for k, src in [
                ("nw", "nw"),
                ("no", "no"),
                ("swc", "Swc"),
                ("sor", "Sor"),
                ("krw_max", "krw_max"),
                ("kro_max", "kro_max"),
                ("mu_w", "mu_w"),
                ("mu_o", "mu_o"),
                ("phi", "phi"),
            ]
        }
        par["sw_init"] = par["swc"] + 1.0e-3
        par["sw_inj"] = 1.0 - par["sor"] - 1.0e-3

        Pe_c = value("Pe_c")
        lambda_c = value("lambda_c")
        Nc = value("Nc")

        target_days = np.asarray(tc["target_days"], dtype=float)
        gate("C15_target_days_exact", target_days.tolist() == TARGET_DAYS_EXPECTED, target_days.tolist())

        theta2 = np.broadcast_to(theta[None, :], (EXPECTED_STREAMLINES, EXPECTED_NODES)).copy()
        dtheta = np.diff(theta2, axis=1)

        M_face_extended = np.empty((EXPECTED_STREAMLINES, EXPECTED_NODES + 1), dtype=float)
        M_face_extended[:, 1:-1] = mf
        M_face_extended[:, 0] = mf[:, 0]
        M_face_extended[:, -1] = mf[:, -1]

        theta_face = np.empty((EXPECTED_STREAMLINES, EXPECTED_NODES + 1), dtype=float)
        theta_face[:, 1:-1] = 0.5 * (theta2[:, :-1] + theta2[:, 1:])
        theta_face[:, 0] = theta2[:, 0]
        theta_face[:, -1] = theta2[:, -1]
        control_volume = np.diff(theta_face, axis=1)

        gate("transport_control_volume_finite", np.isfinite(control_volume).all())
        gate("transport_control_volume_interior_positive", np.all(control_volume[:, 1:] > 0.0))

        target_eta = target_days[:, None] * SECONDS_PER_DAY / te[None, :]
        dt_cfl = float(
            CFL
            * np.min(control_volume[:, 1:])
            / (c17.max_dfw(par) + EPS)
        )
        gate("C17_CFL_step_positive_finite", np.isfinite(dt_cfl) and dt_cfl > 0.0, dt_cfl)

        S = np.full((EXPECTED_STREAMLINES, EXPECTED_NODES), par["sw_init"], dtype=float)
        S[:, 0] = par["sw_inj"]
        eta = np.zeros(EXPECTED_STREAMLINES, dtype=float)
        next_target = np.zeros(EXPECTED_STREAMLINES, dtype=int)
        Y = np.full(EXPECTED_Y_SHAPE, np.nan, dtype=float)

        adv_max = 0.0
        cap_max = 0.0
        preclip_max = 0.0
        steps = 0
        step_ceiling = int(np.ceil(float(np.max(target_eta)) / dt_cfl)) + 109

        print("Generating sealed geology0031 Stage-4 target authority; progress only, no target statistics.")

        while np.any(next_target < 9):
            active = next_target < 9
            goal = np.zeros(EXPECTED_STREAMLINES, dtype=float)
            ii_active = np.where(active)[0]
            goal[ii_active] = target_eta[next_target[ii_active], ii_active]

            dt = np.zeros(EXPECTED_STREAMLINES, dtype=float)
            dt[active] = np.minimum(
                dt_cfl,
                np.maximum(0.0, goal[active] - eta[active]),
            )

            hit = active & (np.abs(goal - eta) <= 5.0e-14)
            if np.any(hit):
                hi = np.where(hit)[0]
                Y[next_target[hi], hi, :] = S[hi, :]
                next_target[hi] += 1
                continue

            S, _, adv_error = c17.adv(S, dt, control_volume, par)
            adv_max = max(adv_max, float(adv_error))
            preclip_max = max(
                preclip_max,
                float(max(
                    0.0,
                    par["swc"] - float(S.min()),
                    float(S.max()) - (1.0 - par["sor"]),
                )),
            )
            np.clip(S, par["swc"], 1.0 - par["sor"], out=S)
            S[:, 0] = par["sw_inj"]

            S, cap_residual = c17.cap(
                S,
                dt,
                par["phi"],
                Pe_c,
                lambda_c,
                mn,
                M_face_extended,
                control_volume,
                dtheta,
                par,
            )
            cap_max = max(cap_max, float(cap_residual))
            preclip_max = max(
                preclip_max,
                float(max(
                    0.0,
                    par["swc"] - float(S.min()),
                    float(S.max()) - (1.0 - par["sor"]),
                )),
            )
            np.clip(S, par["swc"], 1.0 - par["sor"], out=S)
            S[:, 0] = par["sw_inj"]

            eta += dt
            steps += 1

            if steps % 2000 == 0:
                print(
                    f"  step {steps}/{step_ceiling} "
                    f"targets {int(np.sum(next_target))}/{EXPECTED_STREAMLINES * 9}"
                )

            if steps > step_ceiling:
                raise GateError("C17_CFL_step_ceiling_exceeded")

        gate("C17_all_target_snapshots_captured", bool(np.all(next_target == 9)))
        gate("C17_Y_shape_exact", Y.shape == EXPECTED_Y_SHAPE, Y.shape)

        S_min = float(Y.min())
        S_max = float(Y.max())
        temporal_negative_fraction = float(np.mean(np.diff(Y, axis=0) < -1.0e-8))
        spatial_positive_fraction = float(np.mean(np.diff(Y, axis=2) > 1.0e-8))

        target_gates = {
            "finite": bool(np.isfinite(Y).all()),
            "shape": Y.shape == EXPECTED_Y_SHAPE,
            "bounds": max(
                0.0,
                par["swc"] - S_min,
                S_max - (1.0 - par["sor"]),
            ) < 1.0e-8,
            "injector": float(np.max(np.abs(Y[:, :, 0] - par["sw_inj"]))) < 1.0e-12,
            "undershoot": max(
                0.0,
                par["sw_init"] - float(np.min(Y[:, :, 1:])),
            ) < 1.0e-8,
            "adv_conservation": adv_max < 1.0e-11,
            "cap_residual": cap_max < 1.0e-10,
            "preclip": preclip_max < 1.0e-8,
            "temporal": temporal_negative_fraction < 0.01,
            "spatial": spatial_positive_fraction < 0.05,
        }
        for k, v in target_gates.items():
            gate(f"sealed_target_{k}", v)

        target_bytes = deterministic_npz_bytes({
            "Y_transport": Y,
            "target_days": target_days,
            "theta": theta,
            "terminal_pollock_tof_s": te,
            "target_eta": target_eta,
            "M_face_dtheta_dxD": mf,
            "Pe_c": np.array(Pe_c),
            "lambda_c": np.array(lambda_c),
            "Nc_metadata_only": np.array(Nc),
            "case_id": np.array(CASE_ID),
            "partition": np.array("LOCKED_INDEPENDENT_ACCEPTANCE"),
        })

        stage = "seal_authorities"

        artifact_files = {
            "POSTV16_AV1_D_R5A_Derived_V16_Producer_Labels.npz": label_bytes,
            "POSTV16_AV1_D_R5A_Geology0031_Recipe1p1.npz": geology_bytes,
            "POSTV16_AV1_D_R5A_Geology0031_R500_B2000_Flow.npz": flow_bytes,
            "POSTV16_AV1_D_R5A_Geology0031_R500_B2000_SG5_Pollock.pkl": pollock_bytes,
            "POSTV16_AV1_D_R5A_Geology0031_R500_B2000_201Node_C7_FaceMetric.npz": metric_bytes,
            "POSTV16_AV1_D_R5A_Geology0031_R500_B2000_SEALED_Stage4_Target.npz": target_bytes,
        }
        immutable_publish(out, artifact_files)

        artifact_rows = []
        for name in artifact_files:
            p = out / name
            artifact_rows.append({
                "file": name,
                "sha256": sha256_file(p),
                "bytes": p.stat().st_size,
                "sealed": True,
            })

        label_artifact = next(r for r in artifact_rows if r["file"] == "POSTV16_AV1_D_R5A_Derived_V16_Producer_Labels.npz")
        target_artifact = next(r for r in artifact_rows if r["file"].endswith("SEALED_Stage4_Target.npz"))

        authority = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "producer_label_authority": {
                **label_cert,
                "artifact": label_artifact,
            },
            "acceptance_authority": {
                "authority_id": "POSTV16_AV1_LOCKED_INDEPENDENT_ACCEPTANCE_GEOLOGY0031",
                "case_id": CASE_ID,
                "geology": {
                    "id": GEOLOGY_ID,
                    "seed": GEOLOGY_SEED,
                    "recipe": "V16D_SPECTRAL_ENSEMBLE_RECIPE_1.1",
                    "semantics": "deterministic periodic spectral Gaussian random-field sampler; NOT SGS/SGSim",
                },
                "controls": {
                    "CO2_injection_tonnes_per_day": RATE_TPD,
                    "producer_BHP_psi": BHP_PSI,
                    "well_geometry": "FROZEN_V15_FIVE_SPOT",
                },
                "transport": {
                    "streamlines": EXPECTED_STREAMLINES,
                    "nodes": EXPECTED_NODES,
                    "faces": EXPECTED_FACES,
                    "target_days": TARGET_DAYS_EXPECTED,
                    "source_authentic_C17": True,
                    "Pollock_primary": True,
                    "producer_labels_for_acceptance": "SOURCE_AUTHENTIC_SG5_D28",
                },
                "certification": {
                    "geology_gates": geology_gates,
                    "flow_gates": {
                        "finite": finite_flow,
                        "local_relative_L2": local <= 1.0e-9,
                        "global_gross_scaled": global_gross <= 1.0e-9,
                        "global_throughput_scaled": global_throughput <= 1.0e-9,
                        "well_balance_relative": well_balance <= 1.0e-9,
                    },
                    "SG5_source_validation_pass": True,
                    "metric_gates": metric_gates,
                    "target_generation_gates": target_gates,
                },
                "sealed_artifacts": [r for r in artifact_rows if "Geology0031" in r["file"]],
                "sealed_target_sha256": target_artifact["sha256"],
                "firewall": {
                    "model_inference_performed": False,
                    "repair_training_performed": False,
                    "model_checkpoint_loaded": False,
                    "model_performance_computed": False,
                    "target_statistics_published": False,
                    "target_values_printed": False,
                    "acceptance_authority_opened_for_model_evaluation": False,
                    "future_opening_requires_frozen_R5_repaired_checkpoint": True,
                    "no_case_replacement": True,
                    "geology0030_reused": False,
                },
            },
        }

        decision = {
            "derived_V16_producer_labels_certified": True,
            "historical_V15_producer_id_claim": False,
            "label_artifact_sha256": label_artifact["sha256"],
            "geology0031_generated": True,
            "reference_control_physics_generated": True,
            "source_authentic_Stage4_target_generated": True,
            "geology0031_target_sha256": target_artifact["sha256"],
            "authority_SHA_sealed": True,
            "model_inference_performed": False,
            "repair_training_performed": False,
            "target_performance_opened": False,
            "geology0030_reused": False,
            "next": (
                "POSTV16-AV1-D-R5B — execute the single prospectively frozen "
                "producer-balanced C19 TRAIN/VALIDATION repair from the frozen "
                "R3B_RESPONSE checkpoint. Geology0031 remains sealed."
            ),
        }

        contract_files = {
            "PAD_Stream_POSTV16_AV1_D_R5A_Summary.json": json_bytes({
                "milestone": MILESTONE,
                "status": STATUS_PASS,
                "repository_head": head,
                "repository_parent": parent,
                "producer_label_artifact": label_artifact,
                "producer_counts": label_counts,
                "geology0031_target_sha256": target_artifact["sha256"],
                "sealed_artifact_count": len(artifact_rows),
                "sealed_artifacts": artifact_rows,
                "firewall": authority["acceptance_authority"]["firewall"],
                "decision": decision,
            }),
            "POSTV16_AV1_D_R5A_Producer_Label_Certification.json": json_bytes(label_cert),
            "POSTV16_AV1_D_R5A_Sealed_Acceptance_Authority.json": json_bytes(authority),
            "POSTV16_AV1_D_R5A_Decision_Contract.json": json_bytes(decision),
            "POSTV16_AV1_D_R5A_Final_Gate_Matrix.csv": csv_bytes(
                [{"gate": k, **v} for k, v in gates.items()]
            ),
        }
        immutable_publish(out, contract_files)

        manifest_rows = []
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name != "POSTV16_AV1_D_R5A_Artifact_Manifest.csv":
                manifest_rows.append({
                    "file": p.name,
                    "sha256": sha256_file(p),
                    "bytes": p.stat().st_size,
                })
        immutable_publish(
            out,
            {"POSTV16_AV1_D_R5A_Artifact_Manifest.csv": csv_bytes(manifest_rows)},
        )

        print("\n" + "=" * 176)
        print("POSTV16-AV1-D-R5A: PASS")
        print("=" * 176)
        print(f"{'Status':92}: {STATUS_PASS}")
        print(f"{'Derived producer labels':92}: {EXPECTED_STREAMLINES} certified")
        print(f"{'Producer counts':92}: {label_counts}")
        print(f"{'Historical V15 producer-id claim':92}: False")
        print(f"{'Foundation/C2 geometry Linf':92}: {xyz_linf:.12e} m")
        print(f"{'Label artifact SHA256':92}: {label_artifact['sha256']}")
        print(f"{'Geology / seed':92}: {GEOLOGY_ID} / {GEOLOGY_SEED}")
        print(f"{'Reference controls':92}: {RATE_TPD:.0f} t/day / {BHP_PSI:.0f} psi")
        print(f"{'Pollock streamlines / nodes':92}: {EXPECTED_STREAMLINES} / {EXPECTED_NODES}")
        print(f"{'Stage4 target shape':92}: {EXPECTED_Y_SHAPE}")
        print(f"{'Sealed geology0031 target SHA256':92}: {target_artifact['sha256']}")
        print(f"{'Model inference / checkpoint loading':92}: False / False")
        print(f"{'Repair training':92}: False")
        print(f"{'Target performance opened':92}: False")
        print(f"{'Geology0030 reused':92}: False")
        print(f"{'NEXT':92}: R5B — frozen single producer-balanced TRAIN/VALIDATION repair")
        print("=" * 176)
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": MILESTONE,
            "status": STATUS_BLOCKED,
            "failed_stage": stage,
            "exception": repr(exc),
            "gates": gates,
            "model_inference": False,
            "repair_training": False,
            "next_action": (
                "Audit only the failed R5A label/generation/certification gate. "
                "Do not change the R5 connectivity rule, substitute a geology seed, "
                "open geology0031 for model evaluation, or start repair training."
            ),
        }
        data = json_bytes(report)
        p = blocked / "POSTV16_AV1_D_R5A_Blocked_Report.json"
        if p.exists() and p.read_bytes() != data:
            p = blocked / (
                "POSTV16_AV1_D_R5A_Blocked_Report_"
                + hashlib.sha256(data).hexdigest()[:12]
                + ".json"
            )
        if not p.exists():
            p.write_bytes(data)

        print("\n" + "=" * 176)
        print("POSTV16-AV1-D-R5A: BLOCKED")
        print("=" * 176)
        print("Failed stage:", stage)
        print("Exception   :", repr(exc))
        print("Report      :", p)
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
    a = parse_args()
    if a.self_test:
        self_test()
        raise SystemExit(0)
    raise SystemExit(main(a.project_root, a.drive_root))
