#!/usr/bin/env python
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from typing import Any

import numpy as np

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")

MILESTONE = "POSTV16-AV1-D-R1"
STATUS_PASS = (
    "AV1DR1_CV_SPACE_PHYSICAL_IMPACT_AUDITED_"
    "ABSOLUTE_GRID_SNAPSHOT_MAPBACK_NOT_AUTHORIZED"
)
STATUS_BLOCKED = "AV1DR1_CV_PHYSICAL_IMPACT_REPAIR_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"

PARENT_AV1D_COMMIT = "47c8d6a1e8ca6f968ff6afecf77d98e1be58dd01"

AV1D_RUNNER = "PAD_Stream_POSTV16_AV1_D_Physical_Impact_Deployment_Audit.py"
AV1D_RUNNER_BLOB = "f23a6f527590711b865f7424738b68d68d0ba641"

AV1C_RUNNER = "PAD_Stream_POSTV16_AV1_C_Accuracy_Interpretation_and_Deployment_Path_Decision.py"
AV1C_RUNNER_BLOB = "bc8ef764483aa00222bf715728c68fea526179bb"

B1R1_RUNNER = (
    "PAD_Stream_POSTV16_AV1_B1_R1_C26_to_E37A_Component_Mass_"
    "Representation_Equivalence_Audit.py"
)
B1R1_RUNNER_BLOB = "8d9561d7c85805b82dedc26073c4633f90eeeab6"

C17 = "PAD_Stream_V16C17_Production_Source_Authentic_Y_Transport_Tensor_Generation_and_Certification.py"
C17_BLOB = "310e10853ce6f160ee8c9bd270f2823893bf98d3"

R2 = "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"

E36 = "PAD_Stream_V16E36_Short_Adaptive_SGSim_Rollout_and_Early_Plume_Snapshot_Validation.py"
E36_BLOB = "9ab4035c95a25bd61c649f86c82d88f059cef9e2"

E37A = "PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB = "0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"

SG7A = "PAD_Stream_V15SG7A_Full_Physics_TOF_Transport.py"
SG7A_BLOB = "a4dd47338e7a85f130a6a70d0a41211e38c655f8"

SG7D = "PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"
SG7D_BLOB = "890088c0c0fcab415a2c7351c5079ca8ee12bf82"

SOURCE_BLOBS = {
    AV1D_RUNNER: AV1D_RUNNER_BLOB,
    AV1C_RUNNER: AV1C_RUNNER_BLOB,
    B1R1_RUNNER: B1R1_RUNNER_BLOB,
    C17: C17_BLOB,
    R2: R2_BLOB,
    E36: E36_BLOB,
    E37A: E37A_BLOB,
    SG7A: SG7A_BLOB,
    SG7D: SG7D_BLOB,
}

AV1D_BLOCKED_REL = (
    Path("post_v16")
    / RID
    / "POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"
    / "POSTV16_AV1_D_BLOCKED"
)
AV1D_BLOCKED_REPORT = "POSTV16_AV1_D_Blocked_Report.json"

AV1C_OUT_REL = (
    Path("post_v16")
    / RID
    / "POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"
    / "POSTV16_AV1_C_Accuracy_Interpretation_and_Deployment_Path_Decision"
)
AV1C_SUMMARY = "PAD_Stream_POSTV16_AV1_C_Summary.json"
AV1C_DECISION = "POSTV16_AV1_C_Decision_Contract.json"
AV1C_MANIFEST = "POSTV16_AV1_C_Artifact_Manifest.csv"
AV1C_STATUS = (
    "AV1C_REPRESENTATION_ACCEPTED_NO_REPAIR_"
    "MODEL_DEPLOYMENT_REQUIRES_PHYSICAL_IMPACT_AUDIT"
)

C18R_NAME = "V16C18R_Certified_Conditioning_to_Y_Transport_Dataset.npz"
C18R_SHA = "1b610ad3c90aa827be4c466ed71f3a3b771d0498bd915395096efda057f445f3"

C19_NAME = "V16C19_Leakage_Safe_Split_Assignment.npz"
C19_SHA = "399815504f5ba3a900c02f24e4f9496b3a93c2e472a5faea593507cf9174638a"

WEIGHTS_REL = (
    Path("post_v16")
    / RID
    / "POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"
    / "POSTV16_AV1_A3R3R_C26_Weight_State_Compatibility_Reconstruction"
    / "V16C26_EXP2_Exact_Embedded.weights.h5"
)
WEIGHTS_SHA = "4bf0bde8a68d400a7eee33735ca85b4524b70d14be367f278f7276533443f8f9"

R2_REL = Path(
    "provenance/hybrid_dp/"
    "V16E35_R2_FIRST_CONTROLLED_SGSIM_RUNTIME_STATE_TRANSITION_CONSERVATIVE_CAPILLARY_SPLIT"
)
R2_STATE = "V16E35_R2_First_Accepted_SGSim_Runtime_State_Step0001.npz"

E36_REL = Path(
    "provenance/hybrid_dp/"
    "V16E36_SHORT_ADAPTIVE_SGSIM_ROLLOUT_EARLY_PLUME_VALIDATION"
)
E36_CLOSURE = "V16E36_Final_Closure.json"
E36_CACHE = "V16E36_Certified_Physics_Cache.npz"

OUT_REL = (
    Path("post_v16")
    / RID
    / "POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"
    / "POSTV16_AV1_D_R1_CV_Physical_Impact_and_MapBack_Contract_Repair"
)
BLOCKED_REL = (
    Path("post_v16")
    / RID
    / "POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"
    / "POSTV16_AV1_D_R1_BLOCKED"
)

EXPECTED_STREAMLINES = 1078
EXPECTED_NODES = 201
EXPECTED_CVS = 200
EXPECTED_SAMPLES = 9702
EXPECTED_TEST_STREAMLINES = 161
EXPECTED_DAYS = np.array(
    [30., 60., 100., 150., 250., 365., 500., 750., 1000.],
    dtype=np.float64,
)
EXPECTED_GRID = (15, 50, 50)

# C17 production source uses sw_init = Swc + 1e-3 and
# sw_inj = 1 - Sor - 1e-3 with Swc=Sor=0.2.
C17_INITIAL = 0.201
C17_INJECTED = 0.799

# Existing E36 event contract. This is not a new post-hoc threshold.
BREAKTHROUGH_GAS_CUT = 1.0e-4

# Diagnostic plume-support thresholds measured ABOVE the exact C17 t=0 state.
# These are descriptive only and are never used as deployment acceptance gates.
ACTIVE_INCREMENT = 1.0e-8
VISIBLE_INCREMENT = 1.0e-4


class GateError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
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


def load_npz(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as z:
        return {k: z[k].copy() for k in z.files}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError(f"cannot_load_module:{path}")
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def scalar(x: Any) -> float:
    return float(np.asarray(x).reshape(()))


def json_bytes(obj: Any) -> bytes:
    return (
        json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n"
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


def find_by_name_and_sha(
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
                    hits.append(p)
            except OSError:
                pass
    if not hits:
        raise GateError(f"artifact_not_found_with_exact_sha:{name}:{expected_sha}")
    return sorted(set(hits), key=lambda p: (len(str(p)), str(p)))[0]


def verify_manifest(directory: Path, manifest_name: str) -> dict[str, str]:
    rows = read_csv(directory / manifest_name)
    manifest = {r["file"]: r["sha256"] for r in rows}
    for name, expected in manifest.items():
        p = directory / name
        if not p.is_file():
            raise GateError(f"manifest_file_missing:{name}")
        actual = sha256_file(p)
        if actual != expected:
            raise GateError(f"manifest_SHA_mismatch:{name}:{actual}:{expected}")
    return manifest


def jaccard(a: np.ndarray, b: np.ndarray) -> float:
    aa = np.asarray(a, dtype=bool)
    bb = np.asarray(b, dtype=bool)
    union = int(np.sum(aa | bb))
    if union == 0:
        return 1.0
    return float(np.sum(aa & bb) / union)


def first_breakthrough_day(days: np.ndarray, cuts: np.ndarray) -> float:
    idx = np.flatnonzero(np.asarray(cuts, dtype=np.float64) >= BREAKTHROUGH_GAS_CUT)
    return float(days[idx[0]]) if len(idx) else float("nan")


def same_optional_day(a: float, b: float) -> bool:
    if np.isnan(a) and np.isnan(b):
        return True
    return bool(a == b)


def subsegment_midpoints(
    xyz_m: np.ndarray,
    operator: dict[str, np.ndarray],
) -> np.ndarray:
    s = np.asarray(operator["streamline"], dtype=np.int64)
    n = np.asarray(operator["node"], dtype=np.int64)
    a = np.asarray(operator["alpha"], dtype=np.float64)
    p0 = np.asarray(xyz_m, dtype=np.float64)[s, n]
    p1 = np.asarray(xyz_m, dtype=np.float64)[s, n + 1]
    return (1.0 - a[:, None]) * p0 + a[:, None] * p1


def subsegment_state(
    r2: Any,
    saturation_200: np.ndarray,
    geometry: dict[str, np.ndarray],
    p_ref_gas_pa: float,
) -> dict[str, np.ndarray]:
    sat = np.asarray(saturation_200, dtype=np.float64)
    flat_sat = sat.reshape(-1)
    cv_id = np.asarray(geometry["cv_id"], dtype=np.int64)
    sub_sat = flat_sat[cv_id]
    sub_sg = np.clip(
        sub_sat - float(r2.BACKGROUND_SATURATION),
        0.0,
        float(r2.MAX_INCREMENTAL_CO2_SATURATION),
    )
    rho = np.asarray(
        r2.gas_density_from_state(
            sub_sat,
            np.asarray(geometry["pseg_psi"], dtype=np.float64),
            p_ref_gas_pa,
        ),
        dtype=np.float64,
    )
    sub_mass = (
        np.asarray(geometry["pv_m3"], dtype=np.float64)
        * rho
        * sub_sg
    )
    return {
        "saturation": sub_sat,
        "incremental_sg": sub_sg,
        "mass_kg": sub_mass,
    }


def mass_centroid(
    positive_mass_kg: np.ndarray,
    xyz_mid: np.ndarray,
) -> np.ndarray:
    w = np.asarray(positive_mass_kg, dtype=np.float64)
    xyz = np.asarray(xyz_mid, dtype=np.float64)
    total = float(np.sum(w))
    if total <= 0.0:
        return np.full(3, np.nan, dtype=np.float64)
    return np.sum(w[:, None] * xyz, axis=0) / total


def centroid_distance(a: np.ndarray, b: np.ndarray) -> float:
    aa = np.asarray(a, dtype=np.float64)
    bb = np.asarray(b, dtype=np.float64)
    if not (np.isfinite(aa).all() and np.isfinite(bb).all()):
        return float("nan")
    return float(np.linalg.norm(aa - bb))


def cell_support_mask(
    subsegment_condition: np.ndarray,
    flat_cell: np.ndarray,
    n_cells: int,
) -> np.ndarray:
    cond = np.asarray(subsegment_condition, dtype=bool)
    flat = np.asarray(flat_cell, dtype=np.int64)
    count = np.bincount(
        flat[cond],
        minlength=n_cells,
    )
    return count > 0


def producer_snapshot(
    r2: Any,
    e37a: Any,
    sg7a: Any,
    sat200: np.ndarray,
    labels: np.ndarray,
    weights_m3_day: np.ndarray,
    face_pressure_psi: np.ndarray,
    p_ref_gas_pa: float,
    xi_faces: np.ndarray,
) -> tuple[list[dict[str, Any]], float]:
    sat = np.asarray(sat200, dtype=np.float64)
    outlet = sat[:, -1]
    ff = np.asarray(sg7a.fractional_flow(outlet), dtype=np.float64)
    rho = np.asarray(
        r2.gas_density_from_state(
            outlet,
            np.asarray(face_pressure_psi, dtype=np.float64)[:, -1],
            p_ref_gas_pa,
        ),
        dtype=np.float64,
    )
    u_face = np.asarray(sg7a.u_dimensionless(xi_faces), dtype=np.float64)
    mass_flux = (
        np.asarray(weights_m3_day, dtype=np.float64)
        * float(u_face[-1])
        * ff
        * rho
    )
    rows, aggregate = e37a.producer_rows_from_flux(
        labels,
        weights_m3_day,
        ff,
        mass_flux,
        1.0,
    )
    return rows, float(aggregate)


def self_test() -> None:
    a = np.array([True, True, False, False])
    b = np.array([True, False, True, False])
    if abs(jaccard(a, b) - 1.0 / 3.0) > 1.0e-15:
        raise RuntimeError("self_test_jaccard")
    days = np.array([30.0, 60.0, 100.0])
    cuts = np.array([0.0, 1.0e-5, 1.0e-3])
    if first_breakthrough_day(days, cuts) != 100.0:
        raise RuntimeError("self_test_breakthrough")
    xyz = np.array([[0.,0.,0.],[2.,0.,0.]])
    c = mass_centroid(np.array([1.,3.]), xyz)
    if np.max(np.abs(c - np.array([1.5,0.,0.]))) > 1e-15:
        raise RuntimeError("self_test_centroid")
    print("POSTV16-AV1-D-R1 self-test: PASS")


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

    print("=" * 168)
    print("POSTV16-AV1-D-R1 — CV/STREAMLINE PHYSICAL-IMPACT AUDIT + ABSOLUTE MAPBACK CONTRACT REPAIR")
    print("=" * 168)
    print("PARENT AV1-D BLOCK IS PRESERVED, NOT BYPASSED.")
    print("R1 FIRST REPRODUCES THE DAY-30 ABSOLUTE GRID CAPACITY FAILURE.")
    print("C17 IS A STREAMLINE/TOF AUTHORITY; R1 DOES NOT INVENT AN ABSOLUTE C17 GRID TRUTH.")
    print("PHYSICAL IMPACT IS EVALUATED IN EXACT E37A CV MASS + POLLOCK/SUBSEGMENT GEOMETRY.")
    print("NO TRAINING/RETUNING. NO TRANSPORT TIME MARCH. NO GRID-SATURATION PLUME CLAIM.")
    print("NO NEW NUMERICAL DEPLOYMENT-ACCURACY THRESHOLD.\n")

    try:
        root = root.resolve()
        drive = drive.resolve()

        head = git_text(root, "rev-parse", "HEAD")
        parent = git_text(root, "rev-parse", "HEAD^")
        status = git_text(root, "status", "--porcelain")

        gate(
            "repository_parent_is_blocked_AV1D_commit",
            parent == PARENT_AV1D_COMMIT,
            parent,
        )
        gate("repository_clean", status == "", repr(status))

        for fname, blob in SOURCE_BLOBS.items():
            p = root / fname
            actual = git_blob_sha(p, root) if p.is_file() else "missing"
            gate(
                f"{Path(fname).stem}_git_blob_exact",
                actual == blob,
                actual,
            )

        c17_text = (root / C17).read_text(encoding="utf-8")
        gate(
            "C17_initial_state_rule_exact",
            'p["sw_init"]=p["swc"]+1e-3' in c17_text,
        )
        gate(
            "C17_injected_state_rule_exact",
            'p["sw_inj"]=1-p["sor"]-1e-3' in c17_text,
        )

        stage = "parent_failure_binding"

        parent_report_path = drive / AV1D_BLOCKED_REL / AV1D_BLOCKED_REPORT
        gate(
            "parent_AV1D_blocked_report_present",
            parent_report_path.is_file(),
            str(parent_report_path),
        )
        parent_report = load_json(parent_report_path)
        gate(
            "parent_AV1D_failed_stage_physical_snapshot_mapback",
            parent_report.get("failed_stage") == "physical_snapshot_mapback",
            parent_report.get("failed_stage"),
        )
        parent_exc = str(parent_report.get("exception", ""))
        gate(
            "parent_AV1D_failure_is_cell_mass_capacity",
            "capillary_cell_mass_capacity_exceeded" in parent_exc,
            parent_exc,
        )
        match = re.search(
            r"capillary_cell_mass_capacity_exceeded:([0-9eE+\-.]+)",
            parent_exc,
        )
        gate("parent_AV1D_capacity_excess_value_parseable", match is not None)
        parent_excess_kg = float(match.group(1))

        stage = "AV1C_binding"

        av1c_out = drive / AV1C_OUT_REL
        gate("AV1C_output_directory_present", av1c_out.is_dir(), str(av1c_out))
        av1c_manifest = verify_manifest(av1c_out, AV1C_MANIFEST)
        gate("AV1C_manifest_internal_SHA_closure", True, len(av1c_manifest))

        av1c_summary = load_json(av1c_out / AV1C_SUMMARY)
        av1c_decision = load_json(av1c_out / AV1C_DECISION)
        gate(
            "AV1C_status_exact",
            av1c_summary.get("status") == AV1C_STATUS,
            av1c_summary.get("status"),
        )
        gate(
            "AV1C_representation_accepted",
            av1c_decision.get("representation_decision")
            == "ACCEPTED_NO_REPAIR_REQUIRED",
            av1c_decision.get("representation_decision"),
        )
        gate(
            "AV1C_no_retraining_authorized",
            av1c_decision.get("retraining_or_retuning_authorized") is False,
        )

        stage = "authority_binding"

        c18r = find_by_name_and_sha([root, drive], C18R_NAME, C18R_SHA)
        c19 = find_by_name_and_sha([root, drive], C19_NAME, C19_SHA)
        gate("C18R_exact_SHA", sha256_file(c18r) == C18R_SHA, str(c18r))
        gate("C19_exact_SHA", sha256_file(c19) == C19_SHA, str(c19))

        weights = drive / WEIGHTS_REL
        gate("C26_exact_weights_present", weights.is_file(), str(weights))
        actual_weight_sha = sha256_file(weights) if weights.is_file() else "missing"
        gate("C26_exact_weights_SHA", actual_weight_sha == WEIGHTS_SHA, actual_weight_sha)

        r2_state_path = drive / R2_REL / R2_STATE
        e36_closure_path = drive / E36_REL / E36_CLOSURE
        e36_cache_path = drive / E36_REL / E36_CACHE
        for label, p in (
            ("R2_state", r2_state_path),
            ("E36_closure", e36_closure_path),
            ("E36_cache", e36_cache_path),
        ):
            gate(f"{label}_present", p.is_file(), str(p))

        e36_closure = load_json(e36_closure_path)
        e36_cache_sha = sha256_file(e36_cache_path)
        gate(
            "E36_cache_SHA_matches_closure",
            e36_cache_sha == e36_closure.get("certified_cache_sha256"),
            e36_cache_sha,
        )

        stage = "load_physics"

        b1 = load_module(root / B1R1_RUNNER, "postv16_av1dr1_b1")
        r2 = load_module(root / R2, "postv16_av1dr1_r2")
        e36 = load_module(root / E36, "postv16_av1dr1_e36")
        e37a = load_module(root / E37A, "postv16_av1dr1_e37a")
        sg7a = load_module(root / SG7A, "postv16_av1dr1_sg7a")

        with tempfile.TemporaryDirectory(prefix="POSTV16_AV1DR1_SG7D_") as td:
            td = Path(td)
            dst = td / SG7D
            shutil.copy2(root / SG7D, dst)
            sg7d = load_module(dst, "postv16_av1dr1_sg7d")

            cache = load_npz(e36_cache_path)
            parent_state = load_npz(r2_state_path)

            pressure_psi = np.asarray(cache["accepted_pressure_psi"], dtype=np.float64)
            xyz_m = np.asarray(cache["streamline_xyz_m"], dtype=np.float64)
            tau_s = np.asarray(cache["streamline_tof_s"], dtype=np.float64)
            weights_m3_s = np.asarray(cache["streamline_weights_m3_s"], dtype=np.float64)
            xi_faces = np.asarray(cache["xi"], dtype=np.float64)
            labels = np.asarray(cache["producer_labels"]).astype(str)

            gate("pressure_grid_shape_exact", pressure_psi.shape == EXPECTED_GRID, pressure_psi.shape)
            gate(
                "streamline_xyz_shape_exact",
                xyz_m.shape == (EXPECTED_STREAMLINES, EXPECTED_NODES, 3),
                xyz_m.shape,
            )
            gate(
                "streamline_tof_shape_exact",
                tau_s.shape == (EXPECTED_STREAMLINES, EXPECTED_NODES),
                tau_s.shape,
            )
            gate("weights_shape_exact", weights_m3_s.shape == (EXPECTED_STREAMLINES,), weights_m3_s.shape)
            gate("xi_faces_shape_exact", xi_faces.shape == (EXPECTED_NODES,), xi_faces.shape)

            p_ref = scalar(parent_state["co2_density_reference_pressure_pa"])
            weights_m3_day = weights_m3_s * float(e37a.DAY_TO_S)
            tof_days = tau_s / float(e37a.DAY_TO_S)

            operator = sg7d.build_subsegment_operator(
                xyz_m,
                tof_days,
                weights_m3_day,
            )
            geometry = e37a.build_control_volume_geometry(
                r2,
                operator,
                pressure_psi,
                p_ref,
                EXPECTED_STREAMLINES,
                EXPECTED_CVS,
            )
            coeff = np.asarray(geometry["cv_pressure_mass_coeff"], dtype=np.float64)
            gate(
                "E37A_cv_pressure_mass_coeff_shape_exact",
                coeff.shape == (EXPECTED_STREAMLINES, EXPECTED_CVS),
                coeff.shape,
            )
            gate("E37A_cv_pressure_mass_coeff_positive", np.all(coeff > 0.0))

            face_pressure = e37a.build_face_pressure(
                e36,
                sg7d,
                xyz_m,
                pressure_psi,
            )
            gate(
                "E37A_face_pressure_shape_exact",
                face_pressure.shape == (EXPECTED_STREAMLINES, EXPECTED_NODES),
                face_pressure.shape,
            )

            xyz_mid = subsegment_midpoints(xyz_m, operator)
            gate(
                "subsegment_midpoint_shape_exact",
                xyz_mid.shape == (len(operator["pv_m3"]), 3),
                xyz_mid.shape,
            )

            stage = "full_C26_inference"

            d = load_npz(c18r)
            s = load_npz(c19)

            X7 = np.asarray(d["X_sequence_required"], dtype=np.float32)
            Y = np.asarray(d["Y_transport"], dtype=np.float64)
            th = np.asarray(d["target_time_hat"], dtype=np.float32)
            eta_seq = np.asarray(d["target_eta_sequence"], dtype=np.float32)
            sl = np.asarray(d["streamline_index"], dtype=np.int64)
            ti = np.asarray(d["time_index"], dtype=np.int64)
            target_days = np.asarray(d["target_time_days"], dtype=np.float64)
            part = np.asarray(s["sample_partition_code"], dtype=np.int8)

            gate("X7_shape_exact", X7.shape == (EXPECTED_SAMPLES, EXPECTED_NODES, 7), X7.shape)
            gate("Y_shape_exact", Y.shape == (EXPECTED_SAMPLES, EXPECTED_NODES), Y.shape)
            gate("split_shape_exact", part.shape == (EXPECTED_SAMPLES,), part.shape)
            gate(
                "one_sample_per_time_streamline_pair",
                np.array_equal(
                    np.bincount(
                        ti * EXPECTED_STREAMLINES + sl,
                        minlength=len(EXPECTED_DAYS) * EXPECTED_STREAMLINES,
                    ),
                    np.ones(len(EXPECTED_DAYS) * EXPECTED_STREAMLINES, dtype=np.int64),
                ),
            )

            test_samples = np.flatnonzero(part == 2)
            test_streamlines = np.unique(sl[test_samples])
            gate(
                "locked_test_streamlines_161",
                len(test_streamlines) == EXPECTED_TEST_STREAMLINES,
                len(test_streamlines),
            )

            T = np.broadcast_to(
                th[:, None, None],
                (EXPECTED_SAMPLES, EXPECTED_NODES, 1),
            ).astype(np.float32)
            X = np.concatenate(
                [X7, T, eta_seq[:, :, None].astype(np.float32)],
                axis=2,
            )
            gate(
                "C26_full_input_shape_exact",
                X.shape == (EXPECTED_SAMPLES, EXPECTED_NODES, 9),
                X.shape,
            )

            import tensorflow as tf
            try:
                tf.config.experimental.enable_op_determinism()
            except Exception:
                pass
            tf.keras.utils.set_random_seed(16021)

            model = b1.build_model(tf)
            gate(
                "C26_model_parameter_count_52033",
                model.count_params() == 52033,
                model.count_params(),
            )
            model.load_weights(weights)
            pred201_flat = model.predict(
                X,
                batch_size=64,
                verbose=0,
            ).astype(np.float64)
            gate(
                "C26_full_prediction_shape_exact",
                pred201_flat.shape == (EXPECTED_SAMPLES, EXPECTED_NODES),
                pred201_flat.shape,
            )
            gate("C26_full_predictions_finite", np.isfinite(pred201_flat).all())

            # Locked-test identity with AV1-C.
            e_test = pred201_flat[test_samples] - Y[test_samples]
            rmse_test = float(np.sqrt(np.mean(e_test * e_test)))
            mae_test = float(np.mean(np.abs(e_test)))
            max_test = float(np.max(np.abs(e_test)))
            av1c_l1 = av1c_summary["level1_metrics"]
            gate(
                "locked_test_rmse_reproduces_AV1C",
                abs(rmse_test - float(av1c_l1["rmse"])) <= 5.0e-6,
                f"{rmse_test} vs {av1c_l1['rmse']}",
            )
            gate(
                "locked_test_mae_reproduces_AV1C",
                abs(mae_test - float(av1c_l1["mae"])) <= 5.0e-6,
                f"{mae_test} vs {av1c_l1['mae']}",
            )
            gate(
                "locked_test_max_abs_reproduces_AV1C",
                abs(max_test - float(av1c_l1["max_abs_error"])) <= 5.0e-5,
                f"{max_test} vs {av1c_l1['max_abs_error']}",
            )

            pred201 = np.empty(
                (len(EXPECTED_DAYS), EXPECTED_STREAMLINES, EXPECTED_NODES),
                dtype=np.float64,
            )
            true201 = np.empty_like(pred201)
            for n in range(EXPECTED_SAMPLES):
                pred201[ti[n], sl[n]] = pred201_flat[n]
                true201[ti[n], sl[n]] = Y[n]

            ids = np.tile(
                np.arange(EXPECTED_STREAMLINES, dtype=np.int64),
                len(EXPECTED_DAYS),
            )
            pred200_flat, pred_mass_flat, _ = b1.project_201_to_200_component_mass(
                r2,
                e37a,
                pred201.reshape(-1, EXPECTED_NODES),
                coeff,
                ids,
            )
            true200_flat, true_mass_flat, _ = b1.project_201_to_200_component_mass(
                r2,
                e37a,
                true201.reshape(-1, EXPECTED_NODES),
                coeff,
                ids,
            )

            pred200 = pred200_flat.reshape(
                len(EXPECTED_DAYS), EXPECTED_STREAMLINES, EXPECTED_CVS
            )
            true200 = true200_flat.reshape(
                len(EXPECTED_DAYS), EXPECTED_STREAMLINES, EXPECTED_CVS
            )
            pred_mass = pred_mass_flat.reshape(
                len(EXPECTED_DAYS), EXPECTED_STREAMLINES, EXPECTED_CVS
            )
            true_mass = true_mass_flat.reshape(
                len(EXPECTED_DAYS), EXPECTED_STREAMLINES, EXPECTED_CVS
            )

            gate("full_pred200_finite", np.isfinite(pred200).all())
            gate("full_true200_finite", np.isfinite(true200).all())

            # Exact C17 t=0 state in the production solver: reservoir at 0.201
            # with the inlet boundary node fixed at 0.799.
            baseline201 = np.full(
                (EXPECTED_STREAMLINES, EXPECTED_NODES),
                C17_INITIAL,
                dtype=np.float64,
            )
            baseline201[:, 0] = C17_INJECTED
            baseline200, baseline_mass, _ = b1.project_201_to_200_component_mass(
                r2,
                e37a,
                baseline201,
                coeff,
                np.arange(EXPECTED_STREAMLINES, dtype=np.int64),
            )
            baseline_sub = subsegment_state(
                r2,
                baseline200,
                geometry,
                p_ref,
            )

            stage = "parent_failure_reproduction"

            # Reproduce exactly the invalid absolute-snapshot construction used
            # by parent AV1-D: S=0.20 Cartesian parent, zero old-CV mass, and
            # absolute day-30 C17 CV state as the new state.
            uniform_grid = np.full(EXPECTED_GRID, float(r2.BACKGROUND_SATURATION))
            zero_cv_sat = np.full(
                (EXPECTED_STREAMLINES, EXPECTED_CVS),
                float(r2.BACKGROUND_SATURATION),
            )
            zero_cv_mass = np.zeros_like(zero_cv_sat)
            day30_true_sat = true200[0]
            day30_true_mass = true_mass[0]

            reproduced_exc = None
            try:
                e37a.map_control_volume_increment_to_grid(
                    r2,
                    uniform_grid,
                    zero_cv_sat,
                    day30_true_sat,
                    zero_cv_mass,
                    day30_true_mass,
                    geometry,
                    pressure_psi,
                    p_ref,
                    float(sg7d.CELL_PORE_VOLUME_M3),
                    float(np.sum(day30_true_mass)),
                )
            except Exception as exc:
                reproduced_exc = repr(exc)

            gate(
                "parent_AV1D_day30_capacity_failure_reproduced",
                reproduced_exc is not None
                and "capillary_cell_mass_capacity_exceeded" in reproduced_exc,
                reproduced_exc,
            )
            m = re.search(
                r"capillary_cell_mass_capacity_exceeded:([0-9eE+\-.]+)",
                reproduced_exc or "",
            )
            gate("reproduced_capacity_excess_value_parseable", m is not None)
            reproduced_excess_kg = float(m.group(1))
            gate(
                "reproduced_capacity_excess_matches_parent",
                abs(reproduced_excess_kg - parent_excess_kg)
                <= max(1.0e-6, 1.0e-10 * abs(parent_excess_kg)),
                (parent_excess_kg, reproduced_excess_kg),
            )

            # Independent diagnostic of why it fails.
            cv_id = np.asarray(geometry["cv_id"], dtype=np.int64)
            flat_cell = np.asarray(geometry["flat_cell"], dtype=np.int64)
            pv = np.asarray(geometry["pv_m3"], dtype=np.float64)
            pseg = np.asarray(geometry["pseg_psi"], dtype=np.float64)
            day30_sub_sat = day30_true_sat.reshape(-1)[cv_id]
            day30_sub_sg = np.clip(
                day30_sub_sat - float(r2.BACKGROUND_SATURATION),
                0.0,
                float(r2.MAX_INCREMENTAL_CO2_SATURATION),
            )
            day30_sub_rho = np.asarray(
                r2.gas_density_from_state(day30_sub_sat, pseg, p_ref),
                dtype=np.float64,
            )
            day30_deposit = np.bincount(
                flat_cell,
                weights=pv * day30_sub_rho * day30_sub_sg,
                minlength=int(np.prod(EXPECTED_GRID)),
            ).reshape(EXPECTED_GRID)

            smax_grid = np.full(EXPECTED_GRID, float(r2.INJECTED_BOUNDARY_SATURATION))
            rho_max_grid = np.asarray(
                r2.gas_density_from_state(smax_grid, pressure_psi, p_ref),
                dtype=np.float64,
            )
            grid_capacity = (
                float(sg7d.CELL_PORE_VOLUME_M3)
                * rho_max_grid
                * float(r2.MAX_INCREMENTAL_CO2_SATURATION)
            )
            capacity_excess = day30_deposit - grid_capacity
            diagnostic_max_excess = float(np.max(capacity_excess))
            overcapacity_cells = int(np.sum(capacity_excess > 0.0))
            total_positive_excess = float(np.sum(np.maximum(capacity_excess, 0.0)))

            gate(
                "independent_capacity_diagnostic_matches_exception",
                abs(diagnostic_max_excess - reproduced_excess_kg)
                <= max(1.0e-6, 1.0e-10 * abs(reproduced_excess_kg)),
                (diagnostic_max_excess, reproduced_excess_kg),
            )
            gate(
                "absolute_day30_C17_snapshot_not_grid_capacity_feasible",
                overcapacity_cells > 0,
                overcapacity_cells,
            )
            gate(
                "absolute_snapshot_from_uniform_background_not_authorized",
                True,
            )
            gate(
                "E37A_incremental_mapback_capacity_guard_preserved",
                True,
            )

            stage = "CV_physical_impact"

            n_cells = int(np.prod(EXPECTED_GRID))
            physical_rows: list[dict[str, Any]] = []
            producer_rows: list[dict[str, Any]] = []

            truth_cuts: list[float] = []
            hybrid_cuts: list[float] = []
            full_cuts: list[float] = []

            truth_centroids = []
            hybrid_centroids = []
            full_centroids = []

            for t_index, day in enumerate(EXPECTED_DAYS):
                true_sat = true200[t_index]
                true_m = true_mass[t_index]
                pred_sat = pred200[t_index]
                pred_m = pred_mass[t_index]

                hybrid_sat = true_sat.copy()
                hybrid_m = true_m.copy()
                hybrid_sat[test_streamlines] = pred_sat[test_streamlines]
                hybrid_m[test_streamlines] = pred_m[test_streamlines]

                hybrid_recon = e37a.cv_mass_from_saturation(
                    r2,
                    hybrid_sat,
                    coeff,
                )
                hybrid_closure = float(
                    np.max(
                        np.abs(hybrid_recon - hybrid_m)
                        / np.maximum(np.abs(hybrid_m), 1.0)
                    )
                )
                gate(
                    f"day_{int(day)}_heldout_hybrid_CV_mass_closure",
                    hybrid_closure <= 1.0e-10,
                    hybrid_closure,
                )

                states = {}
                for label_name, sat, mass in (
                    ("C17_truth", true_sat, true_m),
                    ("heldout_hybrid", hybrid_sat, hybrid_m),
                    ("full_C26", pred_sat, pred_m),
                ):
                    sub = subsegment_state(r2, sat, geometry, p_ref)
                    sub_total = float(np.sum(sub["mass_kg"]))
                    cv_total = float(np.sum(mass))
                    closure = sub_total - cv_total
                    closure_tol = max(1.0e-6, 1.0e-10 * max(abs(cv_total), 1.0))
                    gate(
                        f"day_{int(day)}_{label_name}_CV_to_subsegment_mass_closure",
                        abs(closure) <= closure_tol,
                        closure,
                    )

                    # Increment relative to the exact C17 production t=0 state.
                    delta_sat = sub["saturation"] - baseline_sub["saturation"]
                    delta_mass = sub["mass_kg"] - baseline_sub["mass_kg"]
                    positive_delta_mass = np.maximum(delta_mass, 0.0)
                    negative_delta_mass = np.minimum(delta_mass, 0.0)

                    active_sub = delta_sat > ACTIVE_INCREMENT
                    visible_sub = delta_sat > VISIBLE_INCREMENT
                    active_cells = cell_support_mask(
                        active_sub,
                        flat_cell,
                        n_cells,
                    )
                    visible_cells = cell_support_mask(
                        visible_sub,
                        flat_cell,
                        n_cells,
                    )

                    centroid = mass_centroid(
                        positive_delta_mass,
                        xyz_mid,
                    )

                    states[label_name] = {
                        "sat": sat,
                        "mass": mass,
                        "sub": sub,
                        "delta_sat": delta_sat,
                        "delta_mass": delta_mass,
                        "positive_delta_mass": positive_delta_mass,
                        "negative_delta_mass": negative_delta_mass,
                        "active_sub": active_sub,
                        "visible_sub": visible_sub,
                        "active_cells": active_cells,
                        "visible_cells": visible_cells,
                        "centroid": centroid,
                        "component_mass_total_kg": cv_total,
                        "incremental_mass_total_kg": float(np.sum(delta_mass)),
                        "positive_incremental_mass_total_kg": float(np.sum(positive_delta_mass)),
                        "negative_incremental_mass_total_kg": float(np.sum(negative_delta_mass)),
                    }

                truth = states["C17_truth"]
                hybrid = states["heldout_hybrid"]
                full = states["full_C26"]

                # C17 source certification says there is no reservoir undershoot.
                gate(
                    f"day_{int(day)}_C17_no_negative_incremental_subsegment_mass",
                    float(np.min(truth["delta_mass"])) >= -1.0e-8,
                    float(np.min(truth["delta_mass"])),
                )

                truth_prod, truth_cut = producer_snapshot(
                    r2, e37a, sg7a, true_sat, labels,
                    weights_m3_day, face_pressure, p_ref, xi_faces,
                )
                hybrid_prod, hybrid_cut = producer_snapshot(
                    r2, e37a, sg7a, hybrid_sat, labels,
                    weights_m3_day, face_pressure, p_ref, xi_faces,
                )
                full_prod, full_cut = producer_snapshot(
                    r2, e37a, sg7a, pred_sat, labels,
                    weights_m3_day, face_pressure, p_ref, xi_faces,
                )

                truth_cuts.append(truth_cut)
                hybrid_cuts.append(hybrid_cut)
                full_cuts.append(full_cut)

                gate(
                    f"day_{int(day)}_heldout_breakthrough_classification_matches_truth",
                    (hybrid_cut >= BREAKTHROUGH_GAS_CUT)
                    == (truth_cut >= BREAKTHROUGH_GAS_CUT),
                    (truth_cut, hybrid_cut),
                )
                gate(
                    f"day_{int(day)}_full_C26_breakthrough_classification_matches_truth",
                    (full_cut >= BREAKTHROUGH_GAS_CUT)
                    == (truth_cut >= BREAKTHROUGH_GAS_CUT),
                    (truth_cut, full_cut),
                )

                truth_centroids.append(truth["centroid"])
                hybrid_centroids.append(hybrid["centroid"])
                full_centroids.append(full["centroid"])

                true_inc = float(truth["incremental_mass_total_kg"])
                hybrid_inc = float(hybrid["incremental_mass_total_kg"])
                full_inc = float(full["incremental_mass_total_kg"])

                physical_rows.append({
                    "target_day": float(day),

                    "truth_component_mass_total_kg": float(truth["component_mass_total_kg"]),
                    "heldout_component_mass_total_kg": float(hybrid["component_mass_total_kg"]),
                    "heldout_component_mass_error_kg": (
                        float(hybrid["component_mass_total_kg"])
                        - float(truth["component_mass_total_kg"])
                    ),
                    "heldout_component_mass_abs_relative": (
                        abs(
                            float(hybrid["component_mass_total_kg"])
                            - float(truth["component_mass_total_kg"])
                        )
                        / max(abs(float(truth["component_mass_total_kg"])), 1.0)
                    ),
                    "full_C26_component_mass_total_kg": float(full["component_mass_total_kg"]),
                    "full_C26_component_mass_error_kg": (
                        float(full["component_mass_total_kg"])
                        - float(truth["component_mass_total_kg"])
                    ),
                    "full_C26_component_mass_abs_relative": (
                        abs(
                            float(full["component_mass_total_kg"])
                            - float(truth["component_mass_total_kg"])
                        )
                        / max(abs(float(truth["component_mass_total_kg"])), 1.0)
                    ),

                    "truth_incremental_mass_above_C17_t0_kg": true_inc,
                    "heldout_incremental_mass_above_C17_t0_kg": hybrid_inc,
                    "heldout_incremental_mass_error_kg": hybrid_inc - true_inc,
                    "heldout_incremental_mass_abs_relative": (
                        abs(hybrid_inc - true_inc) / max(abs(true_inc), 1.0)
                    ),
                    "full_C26_incremental_mass_above_C17_t0_kg": full_inc,
                    "full_C26_incremental_mass_error_kg": full_inc - true_inc,
                    "full_C26_incremental_mass_abs_relative": (
                        abs(full_inc - true_inc) / max(abs(true_inc), 1.0)
                    ),

                    "heldout_negative_incremental_mass_kg": float(hybrid["negative_incremental_mass_total_kg"]),
                    "full_C26_negative_incremental_mass_kg": float(full["negative_incremental_mass_total_kg"]),

                    "heldout_visible_subsegment_jaccard": jaccard(
                        hybrid["visible_sub"],
                        truth["visible_sub"],
                    ),
                    "full_C26_visible_subsegment_jaccard": jaccard(
                        full["visible_sub"],
                        truth["visible_sub"],
                    ),
                    "heldout_visible_cell_support_jaccard": jaccard(
                        hybrid["visible_cells"],
                        truth["visible_cells"],
                    ),
                    "full_C26_visible_cell_support_jaccard": jaccard(
                        full["visible_cells"],
                        truth["visible_cells"],
                    ),
                    "heldout_active_cell_support_jaccard": jaccard(
                        hybrid["active_cells"],
                        truth["active_cells"],
                    ),
                    "full_C26_active_cell_support_jaccard": jaccard(
                        full["active_cells"],
                        truth["active_cells"],
                    ),

                    "heldout_incremental_mass_centroid_distance_m": centroid_distance(
                        hybrid["centroid"],
                        truth["centroid"],
                    ),
                    "full_C26_incremental_mass_centroid_distance_m": centroid_distance(
                        full["centroid"],
                        truth["centroid"],
                    ),

                    "truth_aggregate_CO2_cut": truth_cut,
                    "heldout_aggregate_CO2_cut": hybrid_cut,
                    "heldout_aggregate_CO2_cut_abs_error": abs(hybrid_cut - truth_cut),
                    "full_C26_aggregate_CO2_cut": full_cut,
                    "full_C26_aggregate_CO2_cut_abs_error": abs(full_cut - truth_cut),

                    "truth_breakthrough_by_existing_E36_contract": bool(
                        truth_cut >= BREAKTHROUGH_GAS_CUT
                    ),
                    "heldout_breakthrough_by_existing_E36_contract": bool(
                        hybrid_cut >= BREAKTHROUGH_GAS_CUT
                    ),
                    "full_C26_breakthrough_by_existing_E36_contract": bool(
                        full_cut >= BREAKTHROUGH_GAS_CUT
                    ),
                })

                by_name = {}
                for field_name, rows in (
                    ("C17_truth", truth_prod),
                    ("heldout_hybrid", hybrid_prod),
                    ("full_C26", full_prod),
                ):
                    for row in rows:
                        by_name[(field_name, row["producer"])] = row

                producers = sorted({r["producer"] for r in truth_prod})
                for producer in producers:
                    tr = by_name[("C17_truth", producer)]
                    hr = by_name[("heldout_hybrid", producer)]
                    fr = by_name[("full_C26", producer)]
                    producer_rows.append({
                        "target_day": float(day),
                        "producer": producer,
                        "truth_CO2_cut": float(tr["CO2_cut"]),
                        "heldout_CO2_cut": float(hr["CO2_cut"]),
                        "heldout_CO2_cut_abs_error": abs(
                            float(hr["CO2_cut"]) - float(tr["CO2_cut"])
                        ),
                        "full_C26_CO2_cut": float(fr["CO2_cut"]),
                        "full_C26_CO2_cut_abs_error": abs(
                            float(fr["CO2_cut"]) - float(tr["CO2_cut"])
                        ),
                        "truth_CO2_mass_rate_kg_day": float(tr["CO2_mass_rate_kg_day"]),
                        "heldout_CO2_mass_rate_kg_day": float(hr["CO2_mass_rate_kg_day"]),
                        "heldout_CO2_mass_rate_abs_error_kg_day": abs(
                            float(hr["CO2_mass_rate_kg_day"])
                            - float(tr["CO2_mass_rate_kg_day"])
                        ),
                        "heldout_CO2_mass_rate_abs_relative": (
                            abs(
                                float(hr["CO2_mass_rate_kg_day"])
                                - float(tr["CO2_mass_rate_kg_day"])
                            )
                            / max(abs(float(tr["CO2_mass_rate_kg_day"])), 1.0)
                        ),
                        "full_C26_CO2_mass_rate_kg_day": float(fr["CO2_mass_rate_kg_day"]),
                        "full_C26_CO2_mass_rate_abs_error_kg_day": abs(
                            float(fr["CO2_mass_rate_kg_day"])
                            - float(tr["CO2_mass_rate_kg_day"])
                        ),
                        "full_C26_CO2_mass_rate_abs_relative": (
                            abs(
                                float(fr["CO2_mass_rate_kg_day"])
                                - float(tr["CO2_mass_rate_kg_day"])
                            )
                            / max(abs(float(tr["CO2_mass_rate_kg_day"])), 1.0)
                        ),
                    })

            truth_cuts_arr = np.asarray(truth_cuts, dtype=np.float64)
            hybrid_cuts_arr = np.asarray(hybrid_cuts, dtype=np.float64)
            full_cuts_arr = np.asarray(full_cuts, dtype=np.float64)

            truth_bt = first_breakthrough_day(EXPECTED_DAYS, truth_cuts_arr)
            hybrid_bt = first_breakthrough_day(EXPECTED_DAYS, hybrid_cuts_arr)
            full_bt = first_breakthrough_day(EXPECTED_DAYS, full_cuts_arr)

            gate(
                "heldout_first_breakthrough_target_day_matches_truth",
                same_optional_day(hybrid_bt, truth_bt),
                (truth_bt, hybrid_bt),
            )
            gate(
                "full_C26_first_breakthrough_target_day_matches_truth",
                same_optional_day(full_bt, truth_bt),
                (truth_bt, full_bt),
            )

            # No post-hoc magnitude threshold is selected. Only exact
            # provenance/conservation and the pre-existing E36 breakthrough
            # event are gated.
            gate("no_new_numerical_accuracy_acceptance_threshold_introduced", True)
            gate("no_training_or_retuning_performed", True)
            gate("no_transport_time_march_executed", True)
            gate("no_grid_saturation_plume_claim_made", True)
            gate("no_E37A_or_frozen_physics_modified", True)

            # Summaries of measured physical consequences.
            held_mass_rel = np.asarray(
                [r["heldout_incremental_mass_abs_relative"] for r in physical_rows],
                dtype=np.float64,
            )
            full_mass_rel = np.asarray(
                [r["full_C26_incremental_mass_abs_relative"] for r in physical_rows],
                dtype=np.float64,
            )
            held_j = np.asarray(
                [r["heldout_visible_cell_support_jaccard"] for r in physical_rows],
                dtype=np.float64,
            )
            full_j = np.asarray(
                [r["full_C26_visible_cell_support_jaccard"] for r in physical_rows],
                dtype=np.float64,
            )
            held_cent = np.asarray(
                [r["heldout_incremental_mass_centroid_distance_m"] for r in physical_rows],
                dtype=np.float64,
            )
            full_cent = np.asarray(
                [r["full_C26_incremental_mass_centroid_distance_m"] for r in physical_rows],
                dtype=np.float64,
            )
            held_cut = np.abs(hybrid_cuts_arr - truth_cuts_arr)
            full_cut = np.abs(full_cuts_arr - truth_cuts_arr)

            decision = {
                "parent_AV1D_failure_interpretation": (
                    "The blocked parent attempted an absolute C17/C26 CV snapshot "
                    "mapback from a uniform S=0.20 Cartesian grid. E37A is an "
                    "incremental runtime CV-to-grid transfer; the absolute "
                    "construction requests more mass in at least one Cartesian "
                    "cell than its S=0.8 capacity and is therefore rejected."
                ),
                "E37A_capacity_guard_status": "PRESERVED_CORRECTLY",
                "absolute_C17_grid_snapshot_claim_authorized": False,
                "C17_native_authority": "STREAMLINE_TOF_FULL_PHYSICS_TRANSPORT",
                "CV_space_physical_impact_audited": True,
                "heldout_breakthrough_event_preserved": True,
                "full_C26_breakthrough_event_preserved": True,
                "representation_repair_required": False,
                "retraining_or_retuning_authorized": False,
                "final_deployment_accuracy_accepted": False,
                "why_not_final": (
                    "R1 quantifies physical impact in the exact C17/E37A "
                    "streamline-control-volume representation without inventing "
                    "an absolute Cartesian C17 truth. A source-authentic or "
                    "prospectively defined Cartesian-grid compatibility bridge "
                    "is still required before a grid-saturation plume claim."
                ),
                "next": (
                    "POSTV16-AV1-D2 — Cartesian grid compatibility bridge audit: "
                    "bind the existing 100-day full-grid lineage, test whether it "
                    "is compatible with the C17/E37A CV state, and freeze the "
                    "only defensible grid-comparison path before any grid-plume "
                    "deployment acceptance."
                ),
            }

            capacity_diag = {
                "parent_exception": parent_exc,
                "parent_max_cell_capacity_excess_kg": parent_excess_kg,
                "reproduced_exception": reproduced_exc,
                "reproduced_max_cell_capacity_excess_kg": reproduced_excess_kg,
                "independent_max_cell_capacity_excess_kg": diagnostic_max_excess,
                "overcapacity_cell_count": overcapacity_cells,
                "sum_positive_cell_capacity_excess_kg": total_positive_excess,
                "failed_snapshot_day": 30.0,
                "failed_snapshot_field": "C17_truth",
                "absolute_uniform_background_mapback_authorized": False,
                "E37A_incremental_capacity_guard_modified": False,
            }

            summary = {
                "milestone": MILESTONE,
                "status": STATUS_PASS,
                "repository_head": head,
                "repository_parent": parent,
                "capacity_failure_diagnosis": capacity_diag,
                "target_days": EXPECTED_DAYS.tolist(),
                "locked_test_streamline_count": int(len(test_streamlines)),
                "breakthrough_gas_cut_inherited_from_E36": BREAKTHROUGH_GAS_CUT,
                "first_breakthrough_target_day": {
                    "C17_truth": truth_bt,
                    "heldout_hybrid": hybrid_bt,
                    "full_C26": full_bt,
                },
                "heldout_summary": {
                    "incremental_mass_abs_relative_mean": float(np.mean(held_mass_rel)),
                    "incremental_mass_abs_relative_max": float(np.max(held_mass_rel)),
                    "visible_cell_support_jaccard_mean": float(np.mean(held_j)),
                    "visible_cell_support_jaccard_min": float(np.min(held_j)),
                    "incremental_mass_centroid_distance_m_mean": float(np.nanmean(held_cent)),
                    "incremental_mass_centroid_distance_m_max": float(np.nanmax(held_cent)),
                    "aggregate_CO2_cut_abs_error_mean": float(np.mean(held_cut)),
                    "aggregate_CO2_cut_abs_error_max": float(np.max(held_cut)),
                },
                "full_C26_summary": {
                    "incremental_mass_abs_relative_mean": float(np.mean(full_mass_rel)),
                    "incremental_mass_abs_relative_max": float(np.max(full_mass_rel)),
                    "visible_cell_support_jaccard_mean": float(np.mean(full_j)),
                    "visible_cell_support_jaccard_min": float(np.min(full_j)),
                    "incremental_mass_centroid_distance_m_mean": float(np.nanmean(full_cent)),
                    "incremental_mass_centroid_distance_m_max": float(np.nanmax(full_cent)),
                    "aggregate_CO2_cut_abs_error_mean": float(np.mean(full_cut)),
                    "aggregate_CO2_cut_abs_error_max": float(np.max(full_cut)),
                },
                "decision": decision,
                "new_numerical_accuracy_threshold_selected": False,
                "training_or_retuning_performed": False,
                "transport_time_march_executed": False,
                "grid_saturation_plume_claimed": False,
            }

            small_arrays = {
                "target_days": EXPECTED_DAYS,
                "test_streamline_indices": test_streamlines.astype(np.int64),
                "C17_truth_aggregate_CO2_cut": truth_cuts_arr,
                "heldout_hybrid_aggregate_CO2_cut": hybrid_cuts_arr,
                "full_C26_aggregate_CO2_cut": full_cuts_arr,
                "C17_truth_incremental_mass_centroid_xyz_m": np.asarray(truth_centroids, dtype=np.float64),
                "heldout_incremental_mass_centroid_xyz_m": np.asarray(hybrid_centroids, dtype=np.float64),
                "full_C26_incremental_mass_centroid_xyz_m": np.asarray(full_centroids, dtype=np.float64),
            }

            files = {
                "PAD_Stream_POSTV16_AV1_D_R1_Summary.json": json_bytes(summary),
                "POSTV16_AV1_D_R1_Capacity_Failure_Diagnosis.json": json_bytes(capacity_diag),
                "POSTV16_AV1_D_R1_Decision_Contract.json": json_bytes(decision),
                "POSTV16_AV1_D_R1_By_Target_Day_CV_Physical_Impact.csv": csv_bytes(physical_rows),
                "POSTV16_AV1_D_R1_By_Producer_Physical_Impact.csv": csv_bytes(producer_rows),
                "POSTV16_AV1_D_R1_Physical_Diagnostics_Arrays.npz": deterministic_npz_bytes(small_arrays),
                "POSTV16_AV1_D_R1_Final_Gate_Matrix.csv": csv_bytes(
                    [{"gate": k, **v} for k, v in gates.items()]
                ),
            }

            immutable_publish(out, files)

            manifest_rows = []
            for p in sorted(out.iterdir()):
                if p.is_file() and p.name != "POSTV16_AV1_D_R1_Artifact_Manifest.csv":
                    manifest_rows.append({
                        "file": p.name,
                        "sha256": sha256_file(p),
                        "bytes": p.stat().st_size,
                    })
            immutable_publish(
                out,
                {
                    "POSTV16_AV1_D_R1_Artifact_Manifest.csv":
                        csv_bytes(manifest_rows)
                },
            )

            print("\n" + "=" * 168)
            print("POSTV16-AV1-D-R1: PASS")
            print("=" * 168)
            print(f"{'Status':86}: {STATUS_PASS}")
            print(
                f"{'Parent / reproduced max grid-capacity excess (kg)':86}: "
                f"{parent_excess_kg:.12e} / {reproduced_excess_kg:.12e}"
            )
            print(
                f"{'Overcapacity cells / total positive excess (kg)':86}: "
                f"{overcapacity_cells} / {total_positive_excess:.12e}"
            )
            print(
                f"{'Held-out incremental-mass abs relative mean / max':86}: "
                f"{summary['heldout_summary']['incremental_mass_abs_relative_mean']:.12e} / "
                f"{summary['heldout_summary']['incremental_mass_abs_relative_max']:.12e}"
            )
            print(
                f"{'Held-out visible cell-support Jaccard mean / min':86}: "
                f"{summary['heldout_summary']['visible_cell_support_jaccard_mean']:.12e} / "
                f"{summary['heldout_summary']['visible_cell_support_jaccard_min']:.12e}"
            )
            print(
                f"{'Held-out centroid distance mean / max (m)':86}: "
                f"{summary['heldout_summary']['incremental_mass_centroid_distance_m_mean']:.12e} / "
                f"{summary['heldout_summary']['incremental_mass_centroid_distance_m_max']:.12e}"
            )
            print(
                f"{'Held-out aggregate CO2-cut abs error mean / max':86}: "
                f"{summary['heldout_summary']['aggregate_CO2_cut_abs_error_mean']:.12e} / "
                f"{summary['heldout_summary']['aggregate_CO2_cut_abs_error_max']:.12e}"
            )
            print(
                f"{'Full-C26 incremental-mass abs relative mean / max':86}: "
                f"{summary['full_C26_summary']['incremental_mass_abs_relative_mean']:.12e} / "
                f"{summary['full_C26_summary']['incremental_mass_abs_relative_max']:.12e}"
            )
            print(
                f"{'Full-C26 visible cell-support Jaccard mean / min':86}: "
                f"{summary['full_C26_summary']['visible_cell_support_jaccard_mean']:.12e} / "
                f"{summary['full_C26_summary']['visible_cell_support_jaccard_min']:.12e}"
            )
            print(
                f"{'First breakthrough target day truth / heldout / full-C26':86}: "
                f"{truth_bt} / {hybrid_bt} / {full_bt}"
            )
            print(f"{'Absolute Cartesian C17 grid snapshot authorized':86}: False")
            print(f"{'E37A capacity guard preserved':86}: True")
            print(f"{'Retraining / retuning authorized':86}: False")
            print(f"{'Final deployment accepted':86}: False")
            print(
                f"{'NEXT':86}: POSTV16-AV1-D2 — Cartesian grid compatibility bridge audit"
            )
            print("=" * 168)
            return 0

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": MILESTONE,
            "status": STATUS_BLOCKED,
            "failed_stage": stage,
            "exception": repr(exc),
            "gates": gates,
            "training_or_retuning": False,
            "frozen_artifact_mutation": False,
            "next_action": (
                "Audit only the failed AV1-D-R1 gate(s). "
                "Do not alter E37A capacity safeguards and do not claim a "
                "Cartesian grid-saturation plume."
            ),
        }
        data = json_bytes(report)
        p = blocked / "POSTV16_AV1_D_R1_Blocked_Report.json"
        if p.exists() and p.read_bytes() != data:
            p = blocked / (
                "POSTV16_AV1_D_R1_Blocked_Report_"
                + hashlib.sha256(data).hexdigest()[:12]
                + ".json"
            )
        if not p.exists():
            p.write_bytes(data)

        print("\n" + "=" * 168)
        print("POSTV16-AV1-D-R1: BLOCKED")
        print("=" * 168)
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
