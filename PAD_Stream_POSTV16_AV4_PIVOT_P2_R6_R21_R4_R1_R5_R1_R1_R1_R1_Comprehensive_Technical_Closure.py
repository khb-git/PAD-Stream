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
import zipfile
from pathlib import Path
from typing import Any

import numpy as np

M = "POSTV16-AV4-PIVOT-P2-R6-R21-R4-R1-R5-R1-R1-R1-R1"
NAME = "Comprehensive R5 Technical Closure — Authority Paths, Shape Identity, Safe Serialization, and Day375 Pressure Acceptance"

PASS = (
    "AV4PIVOTP2R6R21R4R1R5R1R1R1R1_COMPREHENSIVE_TECHNICAL_CLOSURE_"
    "PASS_DAY375_PRESSURE_REFRESH_ACCEPTED_NO_COUPLED_SCIENCE_RERUN"
)
BLOCK = "AV4PIVOTP2R6R21R4R1R5R1R1R1R1_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "781ec98aef8bad7b754575b7d36894ee8ee25838"

# ---------------------------------------------------------------------------
# Frozen repository authorities
# ---------------------------------------------------------------------------

RUNNERS = [
    (
        "R5",
        "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_"
        "Controlled_SplitState_T1_PressureCapacity_Reconciliation_Execution.py",
        "bfd1baff03c8670e627f526a8495a6a16d739519",
    ),
    (
        "R5R1",
        "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_R1_"
        "Artifact_Serialization_Technical_Closure.py",
        "13ede305428402b839a38b4431779590e62a5277",
    ),
    (
        "R5R1R1",
        "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_R1_R1_"
        "Residual_Sidecar_ShapeIdentity_Technical_Closure.py",
        "cc2044ff47350e5bed5f16e7f7b2b40461bda9ae",
    ),
    (
        "R5R1R1R1",
        "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_R1_R1_R1_"
        "AuthorityPath_and_ShapeIdentity_Technical_Closure.py",
        "35a62157f1d3cc6bebcb6559b712c4c7c313512b",
    ),
    (
        "A2E",
        "PAD_Stream_POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution.py",
        "79a8969233b72b4543edd382a0c3d1028c6dca09",
    ),
    (
        "R2",
        "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py",
        "a127f8730a16e150713420ea547a8de6255550ef",
    ),
    (
        "SG2",
        "PAD_Stream_V15SG2_Anisotropic_Transmissibility.py",
        "7242012d3e758472abc3ee7f543831b92d2cf419",
    ),
    (
        "SG3",
        "PAD_Stream_V15SG3_FiveSpot_Pressure_Solve.py",
        "66a379cd97ee9120f69e7e7e949171541e4918c3",
    ),
    (
        "R3PHYS",
        "PAD_Stream_V16E41R3R2R1_Local_Conservation_Sign_Convention_Repair.py",
        "740c6da03e73906646bf0153633187e749449f31",
    ),
    (
        "PERM",
        "SGSIM_50x50x15_PERM_MD.csv",
        "317dd47d458bc6f880c2e3dc4ec1f69eeb0dd314",
    ),
]

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

R5_TOKEN = "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5"
R5R1_TOKEN = "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_R1"
R5R1R1_TOKEN = "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_R1_R1"
R5R1R1R1_TOKEN = "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_R1_R1_R1"

BLOCK_BINDINGS = [
    {
        "label": "R5",
        "token": R5_TOKEN,
        "path": BASE / f"{R5_TOKEN}_BLOCKED" / f"{R5_TOKEN}_Blocked_Report.json",
        "status": "AV4PIVOTP2R6R21R4R1R5_TECHNICAL_OR_AUTHORITY_BLOCK",
        "stage": "artifact_publication",
        "exception": "ValueError('Object arrays cannot be saved when allow_pickle=False')",
    },
    {
        "label": "R5R1",
        "token": R5R1_TOKEN,
        "path": BASE / f"{R5R1_TOKEN}_BLOCKED" / f"{R5R1_TOKEN}_Blocked_Report.json",
        "status": "AV4PIVOTP2R6R21R4R1R5R1_TECHNICAL_OR_AUTHORITY_BLOCK",
        "stage": "R5_partial_split_state_revalidation",
        "exception": "GateError('partial_state_residual_SHA_exact')",
    },
    {
        "label": "R5R1R1",
        "token": R5R1R1_TOKEN,
        "path": BASE / f"{R5R1R1_TOKEN}_BLOCKED" / f"{R5R1R1_TOKEN}_Blocked_Report.json",
        "status": "AV4PIVOTP2R6R21R4R1R5R1R1_TECHNICAL_OR_AUTHORITY_BLOCK",
        "stage": "R5R1_BLOCK_authority",
        "exception": "GateError('R5R1_BLOCK_present')",
    },
    {
        "label": "R5R1R1R1",
        "token": R5R1R1R1_TOKEN,
        "path": BASE / f"{R5R1R1R1_TOKEN}_BLOCKED" / f"{R5R1R1R1_TOKEN}_Blocked_Report.json",
        "status": "AV4PIVOTP2R6R21R4R1R5R1R1R1_TECHNICAL_OR_AUTHORITY_BLOCK",
        "stage": "R5R1R1_BLOCK_authority",
        "exception": "GateError('R5R1R1_BLOCK_present')",
    },
]

R5_OUT = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_"
    "Controlled_SplitState_T1_Day375_PressureCapacity_Reconciliation_Execution"
)
R5_STATE = "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_Accepted_PressureCompatible_Day375_State.npz"
R5_EPOCH = "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_Accepted_Day375_Pressure_Epoch.npz"
R5_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_Summary.json"
R5_DECISION = "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_Decision_Contract.json"
R5_CONTRACT = "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_Accepted_Pressure_Refresh_Contract.json"

R20 = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R20_Day375_Globally_Reconciled_"
    "Provisional_State_Closure_and_Acceptance_Audit"
)
R20_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R20_Summary.json"
R20_ACCEPTANCE = "POSTV16_AV4_PIVOT_P2_R6_R20_Day375_State_Acceptance_Contract.json"
R20_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R20_Artifact_Manifest.csv"

BASE_AV3 = Path("post_v16") / RID / "POSTV16_AV3_Corey_Relperm_Heterogeneity"
A6E = BASE_AV3 / "POSTV16_AV3_A6_E_Frozen_Checkpoint_LocalPV_R7D_Integration_Execution"
A6E_STATE = "POSTV16_AV3_A6_E_AV3CR0003_Integrated_State.npz"
A6E_STATE_SHA = "f9e3a7bd8c6dcc43d522e0cb99a0cede2bd212fd570085b4faf82dc71af8f803"

OUT_TOKEN = "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R5_R1_R1_R1_R1"
OUT = BASE / (
    f"{OUT_TOKEN}_Comprehensive_Technical_Closure_and_Pressure_Refresh_Acceptance"
)
BLK = BASE / f"{OUT_TOKEN}_BLOCKED"

GRID = (15, 50, 50)
NCELL = 37500
DAY = 375.0
PRESSURE_TOL = 1e-10
SAT_TOL = 1e-10
LINEAR_TOL = 1e-8
CV_TOL = 1e-10
GLOBAL_TOL = 1e-10

REQUIRED_R5_SCIENCE_GATES = (
    "final_pressure_linear_residual",
    "final_fixed_domain_capacity_consistency",
    "final_pressure_fixed_point_consistency",
    "final_saturation_fixed_point_consistency",
    "final_cellwise_mass_reconstruction",
    "final_global_mass_relative_closure",
    "final_saturation_bounds",
    "final_per_CV_sidecar_conservation",
    "final_global_sidecar_conservation",
    "final_pressure_compatible_mass_matches_sidecar_definition",
    "final_global_accepted_mass_unchanged",
    "final_residual_Cartesian_sidecar_immutable",
    "final_residual_Cartesian_sidecar_SHA_exact",
)


class GateError(RuntimeError):
    pass


def gt(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha_array(a: np.ndarray) -> str:
    arr = np.ascontiguousarray(np.asarray(a))
    h = hashlib.sha256()
    h.update(str(arr.dtype).encode("utf-8"))
    h.update(repr(arr.shape).encode("utf-8"))
    h.update(arr.tobytes(order="C"))
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


def deterministic_npz_bytes(arrays: dict[str, Any]) -> bytes:
    outer = io.BytesIO()
    with zipfile.ZipFile(outer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for key in sorted(arrays):
            arr = np.asarray(arrays[key])
            if arr.dtype == object:
                raise GateError(f"object_array_forbidden:{key}")
            b = io.BytesIO()
            np.save(b, arr, allow_pickle=False)
            info = zipfile.ZipInfo(f"{key}.npy", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            zf.writestr(info, b.getvalue())
    return outer.getvalue()


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


def normalize_producer_wi(
    producer_wi: dict[str, list[dict[str, float]]],
    sg3: Any,
) -> dict[str, np.ndarray]:
    rows = []
    for name in sorted(producer_wi):
        well = sg3.PRODUCERS[name]
        for item in producer_wi[name]:
            rows.append({
                "name": str(name),
                "i": int(well["i"]),
                "j": int(well["j"]),
                "k": int(item["k"]),
                "wi_si": float(item["wi_si"]),
                "wi_reference_si": float(item["wi_reference_si"]),
                "mobility_scale": float(item["mobility_scale"]),
                "re_m": float(item["re_m"]),
            })

    return {
        "producer_name": np.asarray([r["name"] for r in rows], dtype="U32"),
        "producer_i": np.asarray([r["i"] for r in rows], dtype=np.int64),
        "producer_j": np.asarray([r["j"] for r in rows], dtype=np.int64),
        "producer_k": np.asarray([r["k"] for r in rows], dtype=np.int64),
        "producer_wi_si": np.asarray([r["wi_si"] for r in rows], dtype=np.float64),
        "producer_wi_reference_si": np.asarray([r["wi_reference_si"] for r in rows], dtype=np.float64),
        "producer_mobility_scale": np.asarray([r["mobility_scale"] for r in rows], dtype=np.float64),
        "producer_re_m": np.asarray([r["re_m"] for r in rows], dtype=np.float64),
    }


def sidecar_conservation(cv: np.ndarray, mass: np.ndarray) -> tuple[float, float]:
    per_cv: dict[int, float] = {}
    total = 0.0
    for c, m in zip(cv.tolist(), mass.tolist()):
        per_cv[int(c)] = per_cv.get(int(c), 0.0) + float(m)
        total += float(m)
    return max((abs(v) for v in per_cv.values()), default=0.0), abs(total)


def static_block_binding_audit(binding: dict[str, Any]) -> tuple[bool, str]:
    token = str(binding["token"])
    path = Path(binding["path"])
    expected_parent = f"{token}_BLOCKED"
    expected_name = f"{token}_Blocked_Report.json"
    ok = path.parent.name == expected_parent and path.name == expected_name
    return ok, f"{path.parent.name}/{path.name}"


def selftest() -> None:
    # Every inherited BLOCK binding must be internally self-consistent.
    for binding in BLOCK_BINDINGS:
        ok, detail = static_block_binding_audit(binding)
        assert ok, (binding["label"], detail)

    # Shape-sensitive SHA contract: same values, different shapes -> different digest.
    x = np.arange(12, dtype=np.float64)
    y = x.reshape(3, 4)
    assert np.array_equal(x.reshape(3, 4), y)
    assert sha_array(x) != sha_array(y)
    assert sha_array(y.reshape(-1, order="C")) == sha_array(x)

    # Producer WI serialization must never contain object dtype.
    class SG3:
        PRODUCERS = {"P1": {"i": 1, "j": 2}}
    wi = {
        "P1": [{
            "k": 0,
            "wi_si": 1.0,
            "wi_reference_si": 0.5,
            "mobility_scale": 2.0,
            "re_m": 3.0,
        }]
    }
    arrs = normalize_producer_wi(wi, SG3)
    assert all(np.asarray(v).dtype != object for v in arrs.values())
    assert len(deterministic_npz_bytes(arrs)) > 0

    print("POSTV16 AV4 PIVOT P2-R6-R21-R4-R1-R5-R1-R1-R1-R1 comprehensive structural self-test: PASS")


def main(root: Path, drive: Path) -> int:
    root = root.resolve()
    drive = drive.resolve()
    out = drive / OUT
    block = drive / BLK
    stage = "preflight"
    gates: list[dict[str, Any]] = []

    def gate(name: str, cond: Any, detail: Any = None) -> None:
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
        summary_path = out / f"PAD_Stream_{OUT_TOKEN}_Summary.json"
        block_path = block / f"{OUT_TOKEN}_Blocked_Report.json"

        if summary_path.is_file():
            print("[PASS] formal comprehensive closure PASS already exists; immutable outcome preserved.")
            return 0
        gate("no_preexisting_comprehensive_closure_BLOCK", not block_path.exists())

        # ------------------------------------------------------------------
        # Static wrapper audit BEFORE reading Drive artifacts.
        # ------------------------------------------------------------------
        stage = "static_wrapper_audit"

        gate("OUT_parent_namespace_exact", OUT.name.startswith(OUT_TOKEN + "_"), OUT.name)
        gate("BLK_namespace_exact", BLK.name == f"{OUT_TOKEN}_BLOCKED", BLK.name)

        seen_paths = set()
        for binding in BLOCK_BINDINGS:
            ok, detail = static_block_binding_audit(binding)
            gate(f"{binding['label']}_BLOCK_binding_static_exact", ok, detail)
            p = str(binding["path"])
            gate(f"{binding['label']}_BLOCK_binding_unique", p not in seen_paths, p)
            seen_paths.add(p)

        # ------------------------------------------------------------------
        # Repository authority.
        # ------------------------------------------------------------------
        stage = "repository_authority"
        gate("branch_exact", gt(root, "branch", "--show-current") == BRANCH)
        gate("parent_is_R5R1R1R1", gt(root, "rev-parse", "HEAD^") == PARENT)
        gate("repository_clean", gt(root, "status", "--porcelain") == "")

        for label, filename, blob in RUNNERS:
            p = root / filename
            gate(f"{label}_file_present", p.is_file(), str(p))
            gate(f"{label}_blob_exact", gt(root, "hash-object", str(p)) == blob)

        # ------------------------------------------------------------------
        # Bind every immutable technical BLOCK explicitly and independently.
        # ------------------------------------------------------------------
        stage = "immutable_BLOCK_authority"
        block_reports: dict[str, dict[str, Any]] = {}
        block_shas: dict[str, str] = {}

        for binding in BLOCK_BINDINGS:
            label = str(binding["label"])
            p = drive / binding["path"]
            gate(f"{label}_BLOCK_present", p.is_file(), str(p))
            report = js(p)
            block_reports[label] = report
            block_shas[label] = sha(p)

            gate(f"{label}_BLOCK_status_exact", report.get("status") == binding["status"], report.get("status"))
            gate(f"{label}_BLOCK_stage_exact", report.get("failed_stage") == binding["stage"], report.get("failed_stage"))
            gate(f"{label}_BLOCK_exception_exact", report.get("exception") == binding["exception"], report.get("exception"))

        # Preservation firewalls.
        b5 = block_reports["R5"]
        gate("R5_preserved_accepted_Day375_state", b5.get("accepted_Day375_state_preserved") is True)
        gate("R5_pressure_not_accepted", b5.get("pressure_refresh_accepted") is False)
        gate("R5_no_automatic_rerun", b5.get("automatic_rerun_authorized") is False)

        for label in ("R5R1", "R5R1R1", "R5R1R1R1"):
            r = block_reports[label]
            gate(f"{label}_pressure_not_accepted", r.get("pressure_refresh_accepted") is False)
            gate(
                f"{label}_no_coupled_science_rerun",
                r.get("coupled_science_rerun_authorized") is False,
            )

        gate("R5R1_preserved_R5_BLOCK", block_reports["R5R1"].get("source_R5_BLOCK_preserved") is True)
        gate("R5R1_preserved_partial_artifact", block_reports["R5R1"].get("source_R5_partial_artifact_preserved") is True)

        gate("R5R1R1_preserved_R5_BLOCK", block_reports["R5R1R1"].get("source_R5_BLOCK_preserved") is True)
        gate("R5R1R1_preserved_R5R1_BLOCK", block_reports["R5R1R1"].get("source_R5R1_BLOCK_preserved") is True)
        gate("R5R1R1_preserved_partial_artifact", block_reports["R5R1R1"].get("source_R5_partial_artifact_preserved") is True)

        gate("R5R1R1R1_preserved_R5_BLOCK", block_reports["R5R1R1R1"].get("source_R5_BLOCK_preserved") is True)
        gate("R5R1R1R1_preserved_R5R1_BLOCK", block_reports["R5R1R1R1"].get("source_R5R1_BLOCK_preserved") is True)
        gate("R5R1R1R1_preserved_R5R1R1_BLOCK", block_reports["R5R1R1R1"].get("source_R5R1R1_BLOCK_preserved") is True)
        gate("R5R1R1R1_preserved_partial_artifact", block_reports["R5R1R1R1"].get("source_R5_partial_artifact_preserved") is True)

        # ------------------------------------------------------------------
        # Recover and bind the R5 science that completed before publication.
        # ------------------------------------------------------------------
        stage = "R5_completed_science_authority"

        completed = b5.get("gates_completed", [])
        gate("R5_gate_matrix_is_list", isinstance(completed, list), type(completed).__name__)
        by_name = {
            str(row.get("gate")): row
            for row in completed
            if isinstance(row, dict) and row.get("gate") is not None
        }

        missing_science = [g for g in REQUIRED_R5_SCIENCE_GATES if g not in by_name]
        failed_science = [
            g for g in REQUIRED_R5_SCIENCE_GATES
            if g in by_name and by_name[g].get("pass") is not True
        ]
        gate("all_required_R5_final_science_gates_present", not missing_science, missing_science)
        gate("all_required_R5_final_science_gates_PASS", not failed_science, failed_science)

        # ------------------------------------------------------------------
        # Partial R5 artifact authority.
        # ------------------------------------------------------------------
        stage = "R5_partial_artifact_authority"

        r5out = drive / R5_OUT
        state_path = r5out / R5_STATE
        gate("R5_partial_pressure_compatible_state_present", state_path.is_file(), str(state_path))
        partial_state_sha = sha(state_path)

        gate("R5_epoch_absent_after_BLOCK", not (r5out / R5_EPOCH).exists())
        gate("R5_summary_absent_after_BLOCK", not (r5out / R5_SUMMARY).exists())
        gate("R5_decision_absent_after_BLOCK", not (r5out / R5_DECISION).exists())
        gate("R5_contract_absent_after_BLOCK", not (r5out / R5_CONTRACT).exists())

        with np.load(state_path, allow_pickle=False) as z:
            required = [
                "state_day",
                "source_R20_accepted_state_sha256",
                "base_accepted_grid_mass_kg",
                "pressure_reconciliation_sidecar_cv",
                "pressure_reconciliation_sidecar_cell",
                "pressure_reconciliation_sidecar_mass_kg",
                "pressure_compatible_grid_mass_kg",
                "residual_cartesian_sidecar_kg",
                "residual_cartesian_sidecar_sha256",
                "pressure_compatible_saturation",
                "refreshed_pressure_psi",
                "reference_gas_pressure_pa",
                "frozen_T1_domain_flat_cell",
                "pressure_refresh_accepted",
                "physical_time_advanced",
            ]
            missing = [k for k in required if k not in z.files]
            gate("R5_partial_state_schema_complete", not missing, missing)

            state_day = float(np.asarray(z["state_day"]).reshape(()))
            source_r20_sha = str(np.asarray(z["source_R20_accepted_state_sha256"]).reshape(()))
            base_mass = np.asarray(z["base_accepted_grid_mass_kg"], dtype=float)
            sidecar_cv = np.asarray(z["pressure_reconciliation_sidecar_cv"], dtype=np.int64).reshape(-1)
            sidecar_cell = np.asarray(z["pressure_reconciliation_sidecar_cell"], dtype=np.int64).reshape(-1)
            sidecar_mass = np.asarray(z["pressure_reconciliation_sidecar_mass_kg"], dtype=float).reshape(-1)
            final_mass = np.asarray(z["pressure_compatible_grid_mass_kg"], dtype=float)
            residual_cartesian = np.asarray(z["residual_cartesian_sidecar_kg"], dtype=float)
            residual_sha_embedded = str(np.asarray(z["residual_cartesian_sidecar_sha256"]).reshape(()))
            final_sat = np.asarray(z["pressure_compatible_saturation"], dtype=float)
            final_pressure = np.asarray(z["refreshed_pressure_psi"], dtype=float)
            p_ref = float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))
            frozen_domain = np.asarray(z["frozen_T1_domain_flat_cell"], dtype=np.int64).reshape(-1)
            embedded_pressure_marker = bool(np.asarray(z["pressure_refresh_accepted"]).reshape(()))
            physical_time_advanced = bool(np.asarray(z["physical_time_advanced"]).reshape(()))

        gate("R5_partial_state_day_375", state_day == DAY, state_day)
        gate("R5_partial_state_shapes_exact", all(
            a.shape == GRID
            for a in (base_mass, final_mass, residual_cartesian, final_sat, final_pressure)
        ))
        gate("R5_partial_sidecar_lengths_exact", len(sidecar_cv) == len(sidecar_cell) == len(sidecar_mass))
        gate("R5_partial_embedded_pressure_marker_historical_true", embedded_pressure_marker is True)
        gate("R5_partial_no_time_advance", physical_time_advanced is False)

        # ------------------------------------------------------------------
        # R20 accepted transport authority.
        # ------------------------------------------------------------------
        stage = "R20_accepted_transport_authority"

        r20 = drive / R20
        manifest(r20, R20_MANIFEST)
        s20 = js(r20 / R20_SUMMARY)
        a20 = js(r20 / R20_ACCEPTANCE)
        accepted_sha = str(a20["accepted_Day375_state_sha256"])
        gate("R20_state_accepted", a20.get("accepted_Day375_state") is True)
        gate("R20_SHA_matches_summary", accepted_sha == s20["accepted_Day375_state_sha256"])
        gate("R5_partial_source_R20_SHA_exact", source_r20_sha == accepted_sha, source_r20_sha)

        # ------------------------------------------------------------------
        # Split-state and shape-identity closure.
        # ------------------------------------------------------------------
        stage = "split_state_and_shape_identity_closure"

        max_cv_sidecar, global_sidecar = sidecar_conservation(sidecar_cv, sidecar_mass)
        gate("partial_state_per_CV_sidecar_conservative", max_cv_sidecar <= CV_TOL, max_cv_sidecar)
        gate("partial_state_global_sidecar_conservative", global_sidecar <= GLOBAL_TOL, global_sidecar)

        sidecar_grid = np.bincount(
            sidecar_cell,
            weights=sidecar_mass,
            minlength=NCELL,
        ).reshape(GRID)

        mass_definition_error = max_abs(base_mass + sidecar_grid - final_mass)
        gate(
            "pressure_compatible_mass_exact_from_base_plus_sidecar",
            mass_definition_error <= 1e-12,
            mass_definition_error,
        )
        gate(
            "pressure_compatible_global_mass_unchanged",
            abs(float(np.sum(final_mass) - np.sum(base_mass))) <= 1e-7,
            float(np.sum(final_mass) - np.sum(base_mass)),
        )

        residual_shape = tuple(int(x) for x in residual_cartesian.shape)
        residual_flat = np.ascontiguousarray(residual_cartesian).reshape(-1, order="C")
        residual_flat_sha = sha_array(residual_flat)
        residual_grid_sha = sha_array(residual_cartesian)

        gate("stored_residual_shape_is_GRID", residual_shape == GRID, residual_shape)
        gate(
            "original_R5_flat_shape_SHA_recovered_exactly",
            residual_flat_sha == residual_sha_embedded,
            {"embedded": residual_sha_embedded, "flat": residual_flat_sha},
        )
        gate(
            "R5R1_shape_sensitive_SHA_failure_reproduced",
            residual_grid_sha != residual_sha_embedded,
            {"embedded_flat": residual_sha_embedded, "GRID": residual_grid_sha},
        )
        roundtrip_error = max_abs(residual_flat.reshape(GRID, order="C") - residual_cartesian)
        gate("flat_GRID_value_roundtrip_exact", roundtrip_error == 0.0, roundtrip_error)

        # ------------------------------------------------------------------
        # Independent final physics revalidation. This is not a coupled rerun.
        # ------------------------------------------------------------------
        stage = "independent_final_physics_revalidation"

        runner_map = {label: filename for label, filename, _blob in RUNNERS}
        a2e = mod(root / runner_map["A2E"], "comprehensive_a2e")
        r2 = mod(root / runner_map["R2"], "comprehensive_r2")
        sg2 = mod(root / runner_map["SG2"], "comprehensive_sg2")
        sg3 = mod(root / runner_map["SG3"], "comprehensive_sg3")
        r3phys = mod(root / runner_map["R3PHYS"], "comprehensive_r3phys")

        control_path = drive / A6E / A6E_STATE
        gate("A6E_state_SHA_exact", control_path.is_file() and sha(control_path) == A6E_STATE_SHA)

        with np.load(control_path, allow_pickle=False) as z:
            phi = np.asarray(z["paired_porosity"], dtype=float)
            nw = np.asarray(z["nw"], dtype=float)
            no = np.asarray(z["no"], dtype=float)
            krw_max = np.asarray(z["krw_max"], dtype=float)
            kro_max = np.asarray(z["kro_max"], dtype=float)

        pore_volume = phi * float(a2e.BULK_VOLUME_M3)
        permeability = np.loadtxt(
            root / runner_map["PERM"],
            skiprows=1,
            dtype=float,
        ).reshape(GRID, order="C")

        mobility = a2e.spatial_mobility(final_sat, nw, no, krw_max, kro_max)
        kx, ky, kz = sg2.build_directional_permeability(permeability)
        kfx, kfy, kfz = sg2.build_face_permeabilities(kx, ky, kz)
        tx_ref, ty_ref, tz_ref = sg3.construct_si_transmissibilities(kfx, kfy, kfz)
        tx, ty, tz, _face = r3phys.build_updated_transmissibilities(
            sg3,
            tx_ref,
            ty_ref,
            tz_ref,
            mobility["lambda_total"],
        )

        A, b, producer_wi = r3phys.assemble_updated_pressure_system(
            sg3,
            permeability,
            tx,
            ty,
            tz,
            mobility["lambda_total"],
        )
        _p_pa, pressure_check, linear_residual = r3phys.solve_updated_pressure(sg3, A, b)

        gate("independent_pressure_linear_residual", linear_residual < LINEAR_TOL, linear_residual)

        pressure_consistency = relative_l2(pressure_check, final_pressure)
        gate(
            "independent_pressure_matches_partial_state",
            pressure_consistency <= PRESSURE_TOL,
            pressure_consistency,
        )

        full_sat = np.full(GRID, float(a2e.INJECTED), dtype=float)
        capacity = np.asarray(
            a2e.local_mass(r2, full_sat, pressure_check, p_ref, pore_volume),
            dtype=float,
        )
        cap_tol = max(1e-8, 1e-12 * max(float(np.max(capacity)), 1.0))
        max_cap_excess = float(np.max(final_mass - capacity))
        gate(
            "independent_final_capacity_closed",
            max_cap_excess <= cap_tol,
            {"maximum_excess_kg": max_cap_excess, "tolerance_kg": cap_tol},
        )

        sg_check = a2e.invert_local_mass(
            r2,
            final_mass,
            pressure_check,
            p_ref,
            pore_volume,
        )
        sat_check = float(a2e.BACKGROUND) + np.asarray(sg_check, dtype=float)

        saturation_consistency = max_abs(sat_check - final_sat)
        gate(
            "independent_saturation_matches_partial_state",
            saturation_consistency <= SAT_TOL,
            saturation_consistency,
        )

        reconstructed_mass = np.asarray(
            a2e.local_mass(
                r2,
                sat_check,
                pressure_check,
                p_ref,
                pore_volume,
            ),
            dtype=float,
        )
        cell_error = max_abs(reconstructed_mass - final_mass)
        cell_tol = max(1e-8, 1e-10 * max(float(np.max(base_mass)), 1.0))
        global_rel = abs(float(np.sum(reconstructed_mass) - np.sum(base_mass))) / max(
            abs(float(np.sum(base_mass))),
            1.0,
        )

        gate(
            "independent_cellwise_mass_reconstruction",
            cell_error <= cell_tol,
            {"error_kg": cell_error, "tolerance_kg": cell_tol},
        )
        gate(
            "independent_global_mass_relative_closure",
            global_rel <= float(a2e.GLOBAL_MASS_REL_TOL),
            global_rel,
        )
        gate(
            "independent_saturation_bounds",
            float(np.min(sat_check)) >= float(a2e.BACKGROUND) - 1e-12
            and float(np.max(sat_check)) <= float(a2e.INJECTED) + 1e-12,
            [float(np.min(sat_check)), float(np.max(sat_check))],
        )

        # ------------------------------------------------------------------
        # Safe non-object pressure epoch serialization.
        # ------------------------------------------------------------------
        stage = "safe_pressure_epoch_serialization"

        producer_arrays = normalize_producer_wi(producer_wi, sg3)
        gate(
            "producer_wi_all_arrays_nonobject",
            all(np.asarray(v).dtype != object for v in producer_arrays.values()),
        )

        epoch_arrays = {
            "canonical_day": np.asarray(DAY, dtype=np.float64),
            "accepted_transport_base_R20_sha256": np.asarray(accepted_sha, dtype="U64"),
            "source_R5_partial_state_sha256": np.asarray(partial_state_sha, dtype="U64"),
            "source_R5_BLOCK_sha256": np.asarray(block_shas["R5"], dtype="U64"),
            "source_R5R1_BLOCK_sha256": np.asarray(block_shas["R5R1"], dtype="U64"),
            "source_R5R1R1_BLOCK_sha256": np.asarray(block_shas["R5R1R1"], dtype="U64"),
            "source_R5R1R1R1_BLOCK_sha256": np.asarray(block_shas["R5R1R1R1"], dtype="U64"),
            "refreshed_pressure_psi": np.asarray(pressure_check, dtype=np.float64),
            "reconciled_saturation": np.asarray(sat_check, dtype=np.float64),
            "pressure_compatible_grid_mass_kg": np.asarray(final_mass, dtype=np.float64),
            "reference_gas_pressure_pa": np.asarray(p_ref, dtype=np.float64),
            "Tx_dynamic": np.asarray(tx, dtype=np.float64),
            "Ty_dynamic": np.asarray(ty, dtype=np.float64),
            "Tz_dynamic": np.asarray(tz, dtype=np.float64),
            "lambda_total": np.asarray(mobility["lambda_total"], dtype=np.float64),
            "pressure_reconciliation_sidecar_cv": sidecar_cv,
            "pressure_reconciliation_sidecar_cell": sidecar_cell,
            "pressure_reconciliation_sidecar_mass_kg": sidecar_mass,
            "residual_cartesian_sidecar_flat_shape_sha256": np.asarray(residual_flat_sha, dtype="U64"),
            "residual_cartesian_sidecar_GRID_shape_sha256": np.asarray(residual_grid_sha, dtype="U64"),
            "frozen_T1_domain_flat_cell": frozen_domain,
            "physical_time_advanced": np.asarray(False, dtype=np.bool_),
            "Darcy_Pollock_TOF_regenerated": np.asarray(False, dtype=np.bool_),
            **producer_arrays,
        }

        # Explicit final pre-write object-dtype scan.
        object_keys = [
            key
            for key, value in epoch_arrays.items()
            if np.asarray(value).dtype == object
        ]
        gate("pressure_epoch_contains_no_object_arrays", not object_keys, object_keys)

        epoch_bytes = deterministic_npz_bytes(epoch_arrays)

        out.mkdir(parents=True, exist_ok=False)
        epoch_name = f"{OUT_TOKEN}_Accepted_Day375_Pressure_Epoch.npz"
        epoch_path = out / epoch_name
        epoch_path.write_bytes(epoch_bytes)
        epoch_sha = sha(epoch_path)

        # ------------------------------------------------------------------
        # Publish formal closure contracts.
        # ------------------------------------------------------------------
        stage = "formal_closure_publication"

        closure = {
            "milestone": M,
            "status": PASS,
            "closure_type": "comprehensive_technical_closure_no_coupled_science_rerun",
            "repository_parent": PARENT,
            "immutable_BLOCK_chain": {
                label: {
                    "sha256": block_shas[label],
                    "status": block_reports[label]["status"],
                    "failed_stage": block_reports[label]["failed_stage"],
                    "exception": block_reports[label]["exception"],
                    "path": str(next(b["path"] for b in BLOCK_BINDINGS if b["label"] == label)),
                }
                for label in ("R5", "R5R1", "R5R1R1", "R5R1R1R1")
            },
            "R5_completed_science": {
                "required_final_science_gate_count": len(REQUIRED_R5_SCIENCE_GATES),
                "all_required_final_science_gates_PASS": True,
                "coupled_fixed_point_rerun": False,
            },
            "residual_sidecar_shape_identity": {
                "original_R5_hash_shape": [NCELL],
                "stored_R5_state_shape": list(GRID),
                "embedded_flat_shape_sha256": residual_sha_embedded,
                "recovered_flat_shape_sha256": residual_flat_sha,
                "stored_GRID_shape_sha256": residual_grid_sha,
                "flat_to_GRID_value_roundtrip_max_abs": roundtrip_error,
                "shape_sensitive_hash_failure_reproduced": True,
            },
            "serialization_repair": {
                "producer_wi_dictionary_serialized_directly": False,
                "producer_completion_count": int(len(producer_arrays["producer_name"])),
                "object_arrays_present": False,
                "pressure_epoch_sha256": epoch_sha,
            },
            "independent_final_state_revalidation_PASS": True,
        }

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": (
                "R6R21R4R1R5R1R1R1R1_COMPREHENSIVE_TECHNICAL_CLOSURE_PASS_"
                "DAY375_PRESSURE_REFRESH_ACCEPTED_R22_DARCY_POLLOCK_TOF_REGENERATION_NEXT"
            ),
            "source_R20_accepted_state_sha256": accepted_sha,
            "source_R5_partial_pressure_compatible_state_sha256": partial_state_sha,
            "source_R5_BLOCK_sha256": block_shas["R5"],
            "source_R5R1_BLOCK_sha256": block_shas["R5R1"],
            "source_R5R1R1_BLOCK_sha256": block_shas["R5R1R1"],
            "source_R5R1R1R1_BLOCK_sha256": block_shas["R5R1R1R1"],
            "accepted_pressure_epoch_sha256": epoch_sha,
            "R5_coupled_science_rerun": False,
            "technical_wrapper_full_audit_completed": True,
            "all_inherited_BLOCK_paths_static_exact": True,
            "R5_final_science_gates_recovered_from_BLOCK_count": len(REQUIRED_R5_SCIENCE_GATES),
            "residual_flat_shape_SHA256": residual_flat_sha,
            "residual_GRID_shape_SHA256": residual_grid_sha,
            "residual_flat_to_GRID_value_identity_max_abs": roundtrip_error,
            "maximum_per_CV_sidecar_residual_kg": max_cv_sidecar,
            "global_sidecar_residual_kg": global_sidecar,
            "independent_pressure_linear_relative_residual": float(linear_residual),
            "independent_pressure_fixed_point_consistency": pressure_consistency,
            "independent_saturation_fixed_point_consistency": saturation_consistency,
            "independent_cellwise_mass_reconstruction_error_kg": cell_error,
            "independent_global_mass_relative_error": global_rel,
            "independent_cell_capacity_max_excess_kg": max_cap_excess,
            "producer_completion_count": int(len(producer_arrays["producer_name"])),
            "pressure_refresh_accepted": True,
            "Darcy_Pollock_TOF_regeneration_executed": False,
            "physical_time_advance_executed": False,
            "P3_authorized": False,
        }

        pressure_contract = {
            "milestone": M,
            "status": PASS,
            "accepted_Day375_pressure_refresh": True,
            "authority_chain": {
                "accepted_transport_base_R20_sha256": accepted_sha,
                "R5_partial_pressure_compatible_state_sha256": partial_state_sha,
                "R5_BLOCK_sha256": block_shas["R5"],
                "R5R1_BLOCK_sha256": block_shas["R5R1"],
                "R5R1R1_BLOCK_sha256": block_shas["R5R1R1"],
                "R5R1R1R1_BLOCK_sha256": block_shas["R5R1R1R1"],
                "accepted_pressure_epoch_sha256": epoch_sha,
            },
            "science_closure": {
                "R5_reached_artifact_publication_after_final_science_gates": True,
                "required_final_science_gates_all_PASS": True,
                "independent_final_state_revalidation_PASS": True,
                "coupled_science_rerun": False,
            },
            "split_state": {
                "residual_flat_shape_sha256": residual_flat_sha,
                "residual_GRID_shape_sha256": residual_grid_sha,
                "residual_flat_to_GRID_value_identity_exact": roundtrip_error == 0.0,
                "maximum_per_CV_sidecar_residual_kg": max_cv_sidecar,
                "global_sidecar_residual_kg": global_sidecar,
                "reverse_H1_to_S0_pullback": False,
            },
            "serialization": {
                "object_arrays_present": False,
                "producer_wi_representation": (
                    "producer_name + producer_i/j/k + producer_wi_si + "
                    "producer_wi_reference_si + producer_mobility_scale + producer_re_m"
                ),
            },
            "downstream_firewall": {
                "Darcy_Pollock_TOF_regenerated": False,
                "physical_time_advanced": False,
                "P3_authorized": False,
            },
        }

        decision = {
            "milestone": M,
            "status": PASS,
            "classification": summary["classification"],
            "P2_R6_R22_authorized": True,
            "P2_R6_R22_name": "Controlled Day375 Accepted-State Darcy/Pollock/TOF Regeneration",
            "P2_R6_R22_must_bind_comprehensive_closure_pressure_epoch_SHA": True,
            "P2_R6_R22_Darcy_flux_regeneration_authorized": True,
            "P2_R6_R22_Pollock_streamline_regeneration_authorized": True,
            "P2_R6_R22_TOF_regeneration_authorized": True,
            "accepted_Day375_transport_state_remains_authoritative": True,
            "accepted_Day375_pressure_refresh": True,
            "physical_time_advance_authorized": False,
            "transport_time_advance_authorized": False,
            "P3_authorized": False,
            "P4_authorized": False,
            "P5_training_authorized": False,
        }

        (out / f"PAD_Stream_{OUT_TOKEN}_Summary.json").write_bytes(jb(summary))
        (out / f"{OUT_TOKEN}_Comprehensive_Technical_Closure_Contract.json").write_bytes(jb(closure))
        (out / f"{OUT_TOKEN}_Accepted_Pressure_Refresh_Contract.json").write_bytes(jb(pressure_contract))
        (out / f"{OUT_TOKEN}_Decision_Contract.json").write_bytes(jb(decision))
        (out / f"{OUT_TOKEN}_Final_Gate_Matrix.csv").write_bytes(csvb(gates))

        manifest_rows = []
        for p in sorted(out.iterdir()):
            if p.is_file():
                manifest_rows.append({
                    "file": p.name,
                    "sha256": sha(p),
                    "bytes": p.stat().st_size,
                })
        (out / f"{OUT_TOKEN}_Artifact_Manifest.csv").write_bytes(csvb(manifest_rows))

        print("=" * 190)
        print(M, "PASS")
        print("Technical wrapper full audit               : True")
        print("R5 / R5-R1 / R5-R1-R1 / R5-R1-R1-R1 BLOCK SHAs:")
        for label in ("R5", "R5R1", "R5R1R1", "R5R1R1R1"):
            print(f"  {label:10s}: {block_shas[label]}")
        print("R5 partial state SHA256                    :", partial_state_sha)
        print("Residual flat-shape SHA256                 :", residual_flat_sha)
        print("Residual GRID-shape SHA256                 :", residual_grid_sha)
        print("Flat->GRID value roundtrip max abs         :", roundtrip_error)
        print("Independent pressure residual              :", linear_residual)
        print("Pressure fixed-point consistency           :", pressure_consistency)
        print("Saturation fixed-point consistency         :", saturation_consistency)
        print("Cell capacity max excess kg                :", max_cap_excess)
        print("Producer completions serialized numerically:", len(producer_arrays["producer_name"]))
        print("Accepted pressure epoch SHA256             :", epoch_sha)
        print("Pressure refresh accepted                  : True")
        print("R22 authorized                             : True")
        print("Physical time advanced / P3                : False / False")
        print("=" * 190)
        return 0

    except Exception as exc:
        block.mkdir(parents=True, exist_ok=True)
        p = block / f"{OUT_TOKEN}_Blocked_Report.json"
        if not p.exists():
            p.write_bytes(jb({
                "milestone": M,
                "status": BLOCK,
                "failed_stage": stage,
                "exception": repr(exc),
                "all_prior_formal_outcomes_preserved": True,
                "R5_coupled_science_rerun_authorized": False,
                "pressure_refresh_accepted": False,
                "Darcy_Pollock_TOF_regeneration_authorized": False,
                "physical_time_advance_authorized": False,
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
