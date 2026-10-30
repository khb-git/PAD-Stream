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

MILESTONE = "POSTV16-AV4-PIVOT-P2-R6-R12"
MILESTONE_NAME = "Day375 Residual Adjacent-Layer Face-Connected Lateral Topology Design Freeze"
R6R11_NAME = "Day375 Residual Beyond-Same-Layer Topology Design Freeze"
R6R10_NAME = "Day375 Residual Third-Stage Support-Extension Topology Design Freeze"
R6R9_NAME = "Day375 Residual Second-Stage Support-Extension Topology Design Freeze"

STATUS_PASS = (
    "AV4PIVOTP2R6R12_DAY375_RESIDUAL_ADJACENT_LAYER_FACE_CONNECTED_LATERAL_"
    "TOPOLOGY_DESIGN_FREEZE_PASS_NO_STATE_MUTATION"
)
STATUS_BLOCK = "AV4PIVOTP2R6R12_TECHNICAL_OR_AUTHORITY_BLOCK"

EXPECTED_BRANCH = "postv16-av4-pivot"
EXPECTED_PARENT = "1845b1c028268fcacde328d48250990dc1f9ba56"

R6R11_RUNNER = (
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R11_"
    "Day375_Residual_BeyondSameLayer_Topology_Design_Freeze.py"
)
R6R11_RUNNER_BLOB = "a94ce35c8862b7922fca38923bd047ef782fa7c8"

R6R10_RUNNER = (
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R10_"
    "Day375_Residual_ThirdStage_SupportExtension_Topology_Design_Freeze.py"
)
R6R10_RUNNER_BLOB = "dd9124c4cf7ac64ffd9c9e7bb98edf24eb8fba75"

R6R9_RUNNER = (
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R9_"
    "Day375_Residual_SecondStage_SupportExtension_Topology_Design_Freeze.py"
)
R6R9_RUNNER_BLOB = "f45c5c4782dc20b8f860fd04860b7b7369bd1c2a"

R8R1R1_RUNNER = (
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R8_R1_R1_"
    "Corrected_Localization_PASS_Artifact_Path_Reconciliation_"
    "and_Technical_Closure.py"
)
R8R1R1_RUNNER_BLOB = "7f3004f7f6152788142ffc555aa23ccd1484cece"

R8R1_RUNNER = (
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R8_R1_"
    "Targetless_Component_Pool_Balance_KeyError_Technical_Closure_"
    "and_Corrected_Localization_Execution.py"
)
R8R1_RUNNER_BLOB = "41cef11e8ba4c374d88ddf9eb99277eb331510c6"

R8_RUNNER = (
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R8_"
    "Day375_Residual_FrozenDomain_Infeasibility_Localization_"
    "and_Minimal_SupportExtension_Design_Freeze.py"
)
R8_RUNNER_BLOB = "3282d333a0232112eefe4ac58fe1059bb984f495"

R6_RUNNER = (
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R6_"
    "Day375_Residual_External_Component_Projection_Authority_"
    "and_Global_State_Closure_Audit.py"
)
R6_RUNNER_BLOB = "c46c8c3cdb35087fcbd2879b8121b2154cae0b0d"

R2_SOURCE = (
    "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_"
    "Split_First_Controlled_Transition.py"
)
R2_SOURCE_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"

SOURCE_BLOBS = {
    R6R11_RUNNER: R6R11_RUNNER_BLOB,
    R6R10_RUNNER: R6R10_RUNNER_BLOB,
    R6R9_RUNNER: R6R9_RUNNER_BLOB,
    R8R1R1_RUNNER: R8R1R1_RUNNER_BLOB,
    R8R1_RUNNER: R8R1_RUNNER_BLOB,
    R8_RUNNER: R8_RUNNER_BLOB,
    R6_RUNNER: R6_RUNNER_BLOB,
    R2_SOURCE: R2_SOURCE_BLOB,
}

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

R6R11_REL = (
    BASE_AV4 /
    "POSTV16_AV4_PIVOT_P2_R6_R11_Day375_Residual_BeyondSameLayer_"
    "Topology_Design_Freeze"
)
R6R11_SUM = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R11_Summary.json"
R6R11_DEC = "POSTV16_AV4_PIVOT_P2_R6_R11_Decision_Contract.json"
R6R11_MAN = "POSTV16_AV4_PIVOT_P2_R6_R11_Artifact_Manifest.csv"
R6R11_AUDIT = "POSTV16_AV4_PIVOT_P2_R6_R11_Vertical_Exact_Feasibility_Audit.csv"
R6R11_FROZEN = "POSTV16_AV4_PIVOT_P2_R6_R11_Frozen_Vertical_Support_Extension.csv"
R6R11_STATUS = (
    "AV4PIVOTP2R6R11_DAY375_RESIDUAL_BEYOND_SAME_LAYER_"
    "TOPOLOGY_DESIGN_FREEZE_PASS_NO_STATE_MUTATION"
)
R6R11_CLASS = (
    "R6R11_SINGLE_VERTICAL_FACE_SHELL_INSUFFICIENT_"
    "RESIDUAL_GROUPS_REQUIRE_ADJACENT_LAYER_LATERAL_TOPOLOGY_DESIGN"
)

R6R10_REL = (
    BASE_AV4 /
    "POSTV16_AV4_PIVOT_P2_R6_R10_Day375_Residual_ThirdStage_"
    "SupportExtension_Topology_Design_Freeze"
)
R6R10_SUM = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R10_Summary.json"
R6R10_DEC = "POSTV16_AV4_PIVOT_P2_R6_R10_Decision_Contract.json"
R6R10_MAN = "POSTV16_AV4_PIVOT_P2_R6_R10_Artifact_Manifest.csv"
R6R10_AUDIT = "POSTV16_AV4_PIVOT_P2_R6_R10_ThirdStage_Exact_Feasibility_Audit.csv"
R6R10_FROZEN = "POSTV16_AV4_PIVOT_P2_R6_R10_Frozen_ThirdStage_Support_Extension.csv"
R6R10_STATUS = (
    "AV4PIVOTP2R6R10_DAY375_RESIDUAL_THIRD_STAGE_SUPPORT_EXTENSION_"
    "TOPOLOGY_DESIGN_FREEZE_PASS_NO_STATE_MUTATION"
)
R6R10_CLASS = (
    "R6R10_THIRD_SAME_LAYER_FACE_SHELL_INSUFFICIENT_"
    "RESIDUAL_GROUPS_REQUIRE_BEYOND_SAME_LAYER_TOPOLOGY_DESIGN"
)

R6R9_REL = (
    BASE_AV4 /
    "POSTV16_AV4_PIVOT_P2_R6_R9_Day375_Residual_SecondStage_"
    "SupportExtension_Topology_Design_Freeze"
)
R6R9_SUM = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R9_Summary.json"
R6R9_DEC = "POSTV16_AV4_PIVOT_P2_R6_R9_Decision_Contract.json"
R6R9_MAN = "POSTV16_AV4_PIVOT_P2_R6_R9_Artifact_Manifest.csv"
R6R9_AUDIT = "POSTV16_AV4_PIVOT_P2_R6_R9_SecondStage_Exact_Feasibility_Audit.csv"
R6R9_FROZEN = "POSTV16_AV4_PIVOT_P2_R6_R9_Frozen_SecondStage_Support_Extension.csv"
R6R9_STATUS = (
    "AV4PIVOTP2R6R9_DAY375_RESIDUAL_SECOND_STAGE_SUPPORT_EXTENSION_"
    "TOPOLOGY_DESIGN_FREEZE_PASS_NO_STATE_MUTATION"
)
R6R9_CLASS = (
    "R6R9_SECOND_SAME_LAYER_FACE_SHELL_INSUFFICIENT_"
    "RESIDUAL_GROUPS_REQUIRE_THIRD_STAGE_TOPOLOGY_DESIGN"
)

R8R1R1_REL = (
    BASE_AV4 /
    "POSTV16_AV4_PIVOT_P2_R6_R8_R1_R1_"
    "Corrected_Localization_PASS_Artifact_Path_Reconciliation_"
    "and_Technical_Closure"
)
R8R1R1_SUM = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R8_R1_R1_Summary.json"
R8R1R1_DEC = "POSTV16_AV4_PIVOT_P2_R6_R8_R1_R1_Decision_Contract.json"
R8R1R1_MAN = "POSTV16_AV4_PIVOT_P2_R6_R8_R1_R1_Artifact_Manifest.csv"
R8R1R1_UNRES = "POSTV16_AV4_PIVOT_P2_R6_R8_R1_R1_Seven_Unresolved_Groups_for_R6_R9.csv"
R8R1R1_STATUS = (
    "AV4PIVOTP2R6R8R1R1_CORRECTED_LOCALIZATION_PASS_ARTIFACT_PATH_"
    "RECONCILIATION_TECHNICAL_CLOSURE_PASS"
)

R8R1_REL = (
    BASE_AV4 /
    "POSTV16_AV4_PIVOT_P2_R6_R8_R1_Day375_Residual_FrozenDomain_"
    "Infeasibility_Localization_and_Minimal_SupportExtension_Design_Freeze"
)
R8R1_SUM = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R8_R1_Summary.json"
R8R1_DEC = "POSTV16_AV4_PIVOT_P2_R6_R8_R1_Decision_Contract.json"
R8R1_MAN = "POSTV16_AV4_PIVOT_P2_R6_R8_R1_Artifact_Manifest.csv"
R8R1_COMPACT = "POSTV16_AV4_PIVOT_P2_R6_R8_R1_Frozen_Compact_Support_Extension.csv"
R8R1_SUM_SHA = "a5e36bbf3602c955ab55dea622ead692bdfd9c8b7143fb02e26c023597234bb9"
R8R1_DEC_SHA = "d1424a010666323d6a09f495f5065499e09314500c9a89005d11bf8f5d587e08"

R7_REL = (
    BASE_AV4 /
    "POSTV16_AV4_PIVOT_P2_R6_R7_Day375_Residual_External_Component_"
    "Exact_Projection_Semantics_Freeze"
)
R7_BASE = "POSTV16_AV4_PIVOT_P2_R6_R7_Baseline_Exact_Feasibility_Audit.csv"
R7_TGT = "POSTV16_AV4_PIVOT_P2_R6_R7_Frozen_Target_CVs.csv"
R7_GRP = "POSTV16_AV4_PIVOT_P2_R6_R7_Prospective_Execution_Groups.csv"
R7_GF = "POSTV16_AV4_PIVOT_P2_R6_R7_Group_Exact_Feasibility_Audit.csv"
R7_MAN = "POSTV16_AV4_PIVOT_P2_R6_R7_Artifact_Manifest.csv"
R7_SUM = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R7_Summary.json"

R6_REL = (
    BASE_AV4 /
    "POSTV16_AV4_PIVOT_P2_R6_R6_Day375_Residual_External_Component_"
    "Projection_Authority_and_Global_State_Closure_Audit"
)
R6_CV = "POSTV16_AV4_PIVOT_P2_R6_R6_Residual_CV_Component_Ownership.csv"

R5_REL = (
    BASE_AV4 /
    "POSTV16_AV4_PIVOT_P2_R6_R5_Controlled_Day375_TerminalSink_"
    "FixedExternal_Local_Projection"
)
R5_SUM = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R5_Summary.json"
R5_STATE = "POSTV16_AV4_PIVOT_P2_R6_R5_Provisional_LocalRepaired_Day375_State.npz"
R5_STATUS = (
    "AV4PIVOTP2R6R5_CONTROLLED_DAY375_TERMINAL_SINK_FIXED_EXTERNAL_"
    "RECURRENT_ELIGIBILITY_EXACT_CV_CONSERVATIVE_LOCAL_PROJECTION_EXECUTION_PASS"
)
R5_SHA = "1553445022f7267d7802f8833d5440d7521433a4cd8b7c06652cffeb6d693e57"

D370_REL = (
    BASE_AV4 /
    "POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_R1_"
    "CompletedComponent_CellMembership_Identity_Repair_and_Controlled_Projection"
)
D370_SUM = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_R1_Summary.json"
D370_STATE = "POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_R1_Repaired_Day370_State.npz"

A2E_REL = BASE_AV4 / "POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution"
A2E_SUM = "PAD_Stream_POSTV16_AV4_A2_E_Summary.json"
A2E_EPOCH = "POSTV16_AV4_A2_E_Refreshed_Flow_Epoch.npz"

OUT_REL = (
    BASE_AV4 /
    "POSTV16_AV4_PIVOT_P2_R6_R12_Day375_Residual_AdjacentLayer_"
    "FaceConnected_Lateral_Topology_Design_Freeze"
)
BLOCK_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P2_R6_R12_BLOCKED"

GRID = (15, 50, 50)
NZ, NY, NX = GRID
NCELL = NZ * NY * NX
NSL = 1078
NCV = 200
NCV_TOTAL = NSL * NCV

BACKGROUND = 0.20
MAX_SG = 0.60
CELL_TOL_KG = 1e-7
CV_TOL_KG = 1e-7
LEDGER_TOL_KG = 1e-6
SIGN_TOL_KG = 1e-10
SLACK_CV_TOL_KG = 1e-7
SLACK_TOTAL_ABS_TOL_KG = 1e-6
SLACK_TOTAL_REL_TOL = 1e-12
POSITIVE_ROOM_TOL_KG = 1e-8

EXPECTED_COMPONENTS = 158
EXPECTED_GROUPS = 87
EXPECTED_R6R9_INPUT = [0, 3, 23, 31, 65, 76, 79]
EXPECTED_R6R10_INPUT = [0, 3, 31, 65, 76, 79]
EXPECTED_R6R11_INPUT = [0, 3, 31, 65, 76, 79]
EXPECTED_UNRESOLVED = [0, 3, 31, 65, 79]
EXPECTED_R8R1_FAILED = 21
EXPECTED_R8R1_T1A = 1
EXPECTED_R8R1_T1B = 13
EXPECTED_R8R1_STILL = 7


class GateError(RuntimeError):
    pass


def git_text(root: Path, *args: str) -> str:
    p = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return (p.stdout or "").strip()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


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


def json_bytes(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True) + "\n").encode("utf-8")


def bool_csv(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def scalar(x: Any) -> float:
    return float(np.asarray(x).reshape(()))


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError(f"cannot_load_module:{path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def ijk(flat: int) -> tuple[int, int, int]:
    k = flat // (NY * NX)
    rem = flat % (NY * NX)
    j = rem // NX
    i = rem % NX
    return k, j, i


def flat_of(k: int, j: int, i: int) -> int:
    return k * (NY * NX) + j * NX + i


def face_neighbors(cells: set[int]) -> set[int]:
    out: set[int] = set()
    for c in cells:
        k, j, i = ijk(int(c))
        for dj, di in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            jj, ii = j + dj, i + di
            if 0 <= jj < NY and 0 <= ii < NX:
                out.add(flat_of(k, jj, ii))
    return out


def vertical_neighbors(cells: set[int]) -> set[int]:
    out: set[int] = set()
    for c in cells:
        k, j, i = ijk(int(c))
        for dk in (-1, 1):
            kk = k + dk
            if 0 <= kk < NZ:
                out.add(flat_of(kk, j, i))
    return out


def adjacent_layer_lateral_neighbors(vertical_cells: set[int]) -> set[int]:
    """One XY face step from already-frozen vertical support cells."""
    return face_neighbors(vertical_cells)


def h2xy_radius2(cells: np.ndarray, s0: set[int]) -> set[int]:
    out: set[int] = set()
    for c in np.asarray(cells, dtype=np.int64).reshape(-1).tolist():
        k, j, i = ijk(int(c))
        for dj in range(-2, 3):
            for di in range(-2, 3):
                d = abs(di) + abs(dj)
                if not (1 <= d <= 2):
                    continue
                jj, ii = j + dj, i + di
                if 0 <= jj < NY and 0 <= ii < NX:
                    h = flat_of(k, jj, ii)
                    if h not in s0:
                        out.add(int(h))
    return out


def verify_manifest(directory: Path, manifest_name: str) -> dict[str, dict[str, str]]:
    rows = read_csv(directory / manifest_name)
    manifest = {r["file"]: r for r in rows}
    for name, row in manifest.items():
        fp = directory / name
        if not fp.is_file():
            raise GateError(f"manifest_missing_file:{name}")
        if sha256_file(fp) != row["sha256"]:
            raise GateError(f"manifest_SHA_mismatch:{name}")
        if fp.stat().st_size != int(row["bytes"]):
            raise GateError(f"manifest_bytes_mismatch:{name}")
    return manifest


def self_test() -> None:
    anchor = flat_of(6, 10, 10)
    lat = adjacent_layer_lateral_neighbors({anchor})
    assert len(lat) == 4
    assert all(ijk(x)[0] == 6 for x in lat)
    assert flat_of(6, 9, 10) in lat and flat_of(6, 10, 11) in lat
    assert EXPECTED_UNRESOLVED == [0, 3, 31, 65, 79]
    print("POSTV16 AV4 PIVOT P2-R6-R12 structural self-test: PASS")


def main(project_root: Path, drive_root: Path) -> int:
    root = Path(project_root).resolve()
    drive = Path(drive_root).resolve()
    out = drive / OUT_REL
    block = drive / BLOCK_REL
    stage = "preflight"
    gates: list[dict[str, Any]] = []

    def gate(name: str, passed: Any, detail: Any = None) -> None:
        ok = bool(passed)
        gates.append({
            "stage": stage,
            "gate": name,
            "pass": ok,
            "detail": "" if detail is None else repr(detail),
        })
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" +
              ("" if detail is None else f" -- {detail}"))
        if not ok:
            raise GateError(name)

    print("=" * 216)
    print("POSTV16-AV4-PIVOT-P2-R6-R12 -- DAY375 RESIDUAL ADJACENT-LAYER FACE-CONNECTED LATERAL TOPOLOGY DESIGN FREEZE")
    print("=" * 216)
    print("DESIGN/FREEZE ONLY. NO DAY375 STATE MUTATION. NO SUPPORT EXECUTION. NO PRESSURE REFRESH. NO TIME ADVANCE.")
    print("ONLY THE FIVE R6-R11 UNRESOLVED GROUPS ARE RE-LOCALIZED.")
    print("T5AL = ONE XY FACE STEP FROM THE FROZEN R6-R11 VERTICAL SUPPORT CELLS IN THEIR ADJACENT LAYERS.")
    print("T5AL CELLS ARE DIRECT TERMINAL-SINK CANDIDATES; THE VERTICAL ANCHOR IS A GEOMETRIC WITNESS, NOT A TRANSIT NODE.")
    print()

    try:
        stage = "formal_outcome_firewall"
        ps = out / "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R12_Summary.json"
        br = block / "POSTV16_AV4_PIVOT_P2_R6_R12_Blocked_Report.json"
        if ps.is_file():
            print("[PASS] formal R6-R12 PASS already exists; immutable outcome preserved.")
            return 0
        gate("no_preexisting_R6R12_BLOCK", not br.exists(), str(br))

        stage = "repository_authority"
        gate("branch_exact", git_text(root, "branch", "--show-current") == EXPECTED_BRANCH)
        parent = git_text(root, "rev-parse", "HEAD^")
        gate("parent_is_R6R11_PASS_commit", parent == EXPECTED_PARENT, parent)
        status = git_text(root, "status", "--porcelain")
        gate("repository_clean", status == "", repr(status))
        for fn, expected_blob in SOURCE_BLOBS.items():
            fp = root / fn
            actual = git_text(root, "hash-object", str(fp)) if fp.is_file() else "missing"
            gate(f"{Path(fn).stem}_blob_exact", actual == expected_blob, actual)

        stage = "R6R8R1R1_authority"
        cdir = drive / R8R1R1_REL
        for name in (R8R1R1_SUM, R8R1R1_DEC, R8R1R1_MAN, R8R1R1_UNRES):
            gate(f"closure_{name}_present", (cdir / name).is_file(), str(cdir / name))
        verify_manifest(cdir, R8R1R1_MAN)
        csum = load_json(cdir / R8R1R1_SUM)
        cdec = load_json(cdir / R8R1R1_DEC)
        unresolved_rows = read_csv(cdir / R8R1R1_UNRES)
        unresolved_ids = sorted(int(r["execution_group_id"]) for r in unresolved_rows)
        gate("closure_status_exact", csum.get("status") == R8R1R1_STATUS, csum.get("status"))
        gate("closure_scientific_LP_not_reexecuted", csum.get("scientific_LP_reexecuted") is False)
        gate("closure_scientific_PASS_bound", csum.get("R8R1_scientific_PASS_bound") is True)
        gate("closure_unresolved_ids_exact", unresolved_ids == EXPECTED_R6R9_INPUT, unresolved_ids)
        gate("closure_R6R9_authorized", cdec.get("P2_R6_R9_authorized") is True)
        gate("closure_R6R9_name_exact", cdec.get("P2_R6_R9_name") == R6R9_NAME, cdec.get("P2_R6_R9_name"))
        gate("closure_projection_execution_false", cdec.get("P2_R6_R9_projection_execution_authorized") is False)
        gate("closure_second_stage_design_true", cdec.get("P2_R6_R9_second_stage_topology_design_authorized") is True)
        gate("closure_support_execution_false", cdec.get("support_growth_execution_authorized_now") is False)
        gate("closure_pressure_false", cdec.get("pressure_refresh_authorized") is False)
        gate("closure_time_false", cdec.get("time_advance_authorized") is False)
        gate("closure_P3_false", cdec.get("P3_authorized") is False)

        stage = "R6R8R1_scientific_binding"
        sdir = drive / R8R1_REL
        gate("R8R1_summary_SHA_exact", sha256_file(sdir / R8R1_SUM) == R8R1_SUM_SHA, sha256_file(sdir / R8R1_SUM))
        gate("R8R1_decision_SHA_exact", sha256_file(sdir / R8R1_DEC) == R8R1_DEC_SHA, sha256_file(sdir / R8R1_DEC))
        verify_manifest(sdir, R8R1_MAN)
        ssum = load_json(sdir / R8R1_SUM)
        gate("R8R1_failed_count_exact", int(ssum["R6R7_failed_group_count_localized"]) == EXPECTED_R8R1_FAILED)
        gate("R8R1_T1A_exact", int(ssum["T1A_connectivity_only_feasible_group_count"]) == EXPECTED_R8R1_T1A)
        gate("R8R1_T1B_exact", int(ssum["T1B_single_shell_new_endpoint_feasible_group_count"]) == EXPECTED_R8R1_T1B)
        gate("R8R1_still_exact", int(ssum["single_shell_still_infeasible_group_count"]) == EXPECTED_R8R1_STILL)
        gate("R8R1_no_state_mutation", ssum.get("state_mutation_executed") is False)
        compact_rows = read_csv(sdir / R8R1_COMPACT)

        stage = "R6R11_scientific_binding"
        r11dir = drive / R6R11_REL
        for name in (R6R11_SUM, R6R11_DEC, R6R11_MAN, R6R11_AUDIT, R6R11_FROZEN):
            gate(f"R6R11_{name}_present", (r11dir / name).is_file(), str(r11dir / name))
        verify_manifest(r11dir, R6R11_MAN)
        r11sum = load_json(r11dir / R6R11_SUM)
        r11dec = load_json(r11dir / R6R11_DEC)
        gate("R6R11_status_exact", r11sum.get("status") == R6R11_STATUS, r11sum.get("status"))
        gate("R6R11_class_exact", r11sum.get("classification") == R6R11_CLASS, r11sum.get("classification"))
        gate("R6R11_input_ids_exact", r11sum.get("input_unresolved_group_ids") == EXPECTED_R6R11_INPUT, r11sum.get("input_unresolved_group_ids"))
        gate("R6R11_T4V_feasible_exact", int(r11sum.get("T4V_exact_feasible_group_count", -1)) == 1, r11sum.get("T4V_exact_feasible_group_count"))
        gate("R6R11_T4V_still_exact", int(r11sum.get("T4V_still_infeasible_group_count", -1)) == 5, r11sum.get("T4V_still_infeasible_group_count"))
        gate("R6R11_unresolved_after_T4V_exact", r11sum.get("unresolved_after_T4V_group_ids") == EXPECTED_UNRESOLVED, r11sum.get("unresolved_after_T4V_group_ids"))
        gate("R6R11_post_T3_deficient_CVs_exact", int(r11sum.get("post_T3_localized_deficient_CV_count", -1)) == 28, r11sum.get("post_T3_localized_deficient_CV_count"))
        gate("R6R11_no_state_mutation", r11sum.get("state_mutation_executed") is False)
        gate("R6R11_vertical_support_used", r11sum.get("vertical_support_used") is True)
        gate("R6R11_vertical_support_not_executed", r11sum.get("vertical_support_executed") is False)
        gate("R6R11_adjacent_layer_lateral_not_used", r11sum.get("adjacent_layer_lateral_support_used") is False)
        gate("R6R11_R6R12_authorized", r11dec.get("P2_R6_R12_authorized") is True)
        gate("R6R11_R6R12_name_exact", r11dec.get("P2_R6_R12_name") == MILESTONE_NAME, r11dec.get("P2_R6_R12_name"))
        gate("R6R11_projection_execution_false", r11dec.get("P2_R6_R12_projection_execution_authorized") is False)
        gate("R6R11_adjacent_layer_lateral_design_true", r11dec.get("P2_R6_R12_adjacent_layer_lateral_topology_design_authorized") is True)
        gate("R6R11_support_execution_false", r11dec.get("support_growth_execution_authorized_now") is False)
        gate("R6R11_pressure_false", r11dec.get("pressure_refresh_authorized") is False)
        gate("R6R11_time_false", r11dec.get("time_advance_authorized") is False)
        gate("R6R11_P3_false", r11dec.get("P3_authorized") is False)
        r11_audit_rows = read_csv(r11dir / R6R11_AUDIT)
        r11_frozen_rows = read_csv(r11dir / R6R11_FROZEN)
        audit_unresolved_t4v = sorted(int(r["execution_group_id"]) for r in r11_audit_rows if not bool_csv(r["T4V_exact_feasible"]))
        gate("R6R11_audit_unresolved_exact", audit_unresolved_t4v == EXPECTED_UNRESOLVED, audit_unresolved_t4v)

        stage = "R6R10_scientific_binding"
        r10dir = drive / R6R10_REL
        for name in (R6R10_SUM, R6R10_DEC, R6R10_MAN, R6R10_AUDIT, R6R10_FROZEN):
            gate(f"R6R10_{name}_present", (r10dir / name).is_file(), str(r10dir / name))
        verify_manifest(r10dir, R6R10_MAN)
        r10sum = load_json(r10dir / R6R10_SUM)
        r10dec = load_json(r10dir / R6R10_DEC)
        gate("R6R10_status_exact", r10sum.get("status") == R6R10_STATUS, r10sum.get("status"))
        gate("R6R10_class_exact", r10sum.get("classification") == R6R10_CLASS, r10sum.get("classification"))
        gate("R6R10_input_ids_exact", r10sum.get("input_unresolved_group_ids") == EXPECTED_R6R10_INPUT, r10sum.get("input_unresolved_group_ids"))
        gate("R6R10_T3_feasible_exact", int(r10sum.get("T3_exact_feasible_group_count", -1)) == 0, r10sum.get("T3_exact_feasible_group_count"))
        gate("R6R10_T3_still_exact", int(r10sum.get("T3_still_infeasible_group_count", -1)) == 6, r10sum.get("T3_still_infeasible_group_count"))
        gate("R6R10_unresolved_after_T3_exact", r10sum.get("unresolved_after_T3_group_ids") == EXPECTED_R6R11_INPUT, r10sum.get("unresolved_after_T3_group_ids"))
        gate("R6R10_post_T2_deficient_CVs_exact", int(r10sum.get("post_T2_localized_deficient_CV_count", -1)) == 28, r10sum.get("post_T2_localized_deficient_CV_count"))
        gate("R6R10_no_state_mutation", r10sum.get("state_mutation_executed") is False)
        gate("R6R10_R6R11_authorized", r10dec.get("P2_R6_R11_authorized") is True)
        gate("R6R10_R6R11_name_exact", r10dec.get("P2_R6_R11_name") == R6R11_NAME, r10dec.get("P2_R6_R11_name"))
        gate("R6R10_projection_execution_false", r10dec.get("P2_R6_R11_projection_execution_authorized") is False)
        gate("R6R10_beyond_same_layer_design_true", r10dec.get("P2_R6_R11_beyond_same_layer_topology_design_authorized") is True)
        gate("R6R10_support_execution_false", r10dec.get("support_growth_execution_authorized_now") is False)
        gate("R6R10_pressure_false", r10dec.get("pressure_refresh_authorized") is False)
        gate("R6R10_time_false", r10dec.get("time_advance_authorized") is False)
        gate("R6R10_P3_false", r10dec.get("P3_authorized") is False)
        r10_audit_rows = read_csv(r10dir / R6R10_AUDIT)
        r10_frozen_rows = read_csv(r10dir / R6R10_FROZEN)
        audit_unresolved_t3 = sorted(int(r["execution_group_id"]) for r in r10_audit_rows if not bool_csv(r["T3_exact_feasible"]))
        gate("R6R10_audit_unresolved_exact", audit_unresolved_t3 == EXPECTED_R6R11_INPUT, audit_unresolved_t3)

        stage = "R6R9_scientific_binding"
        r9dir = drive / R6R9_REL
        for name in (R6R9_SUM, R6R9_DEC, R6R9_MAN, R6R9_AUDIT, R6R9_FROZEN):
            gate(f"R6R9_{name}_present", (r9dir / name).is_file(), str(r9dir / name))
        verify_manifest(r9dir, R6R9_MAN)
        r9sum = load_json(r9dir / R6R9_SUM)
        r9dec = load_json(r9dir / R6R9_DEC)
        gate("R6R9_status_exact", r9sum.get("status") == R6R9_STATUS, r9sum.get("status"))
        gate("R6R9_class_exact", r9sum.get("classification") == R6R9_CLASS, r9sum.get("classification"))
        gate("R6R9_input_ids_exact", r9sum.get("input_unresolved_group_ids") == EXPECTED_R6R9_INPUT, r9sum.get("input_unresolved_group_ids"))
        gate("R6R9_T2_feasible_exact", int(r9sum.get("T2_exact_feasible_group_count", -1)) == 1, r9sum.get("T2_exact_feasible_group_count"))
        gate("R6R9_T2_still_exact", int(r9sum.get("T2_still_infeasible_group_count", -1)) == 6, r9sum.get("T2_still_infeasible_group_count"))
        gate("R6R9_unresolved_after_T2_exact", r9sum.get("unresolved_after_T2_group_ids") == EXPECTED_R6R10_INPUT, r9sum.get("unresolved_after_T2_group_ids"))
        gate("R6R9_post_T1B_deficient_CVs_exact", int(r9sum.get("post_T1B_localized_deficient_CV_count", -1)) == 42, r9sum.get("post_T1B_localized_deficient_CV_count"))
        gate("R6R9_no_state_mutation", r9sum.get("state_mutation_executed") is False)
        gate("R6R9_R6R10_authorized", r9dec.get("P2_R6_R10_authorized") is True)
        gate("R6R9_R6R10_name_exact", r9dec.get("P2_R6_R10_name") == R6R10_NAME, r9dec.get("P2_R6_R10_name"))
        gate("R6R9_projection_execution_false", r9dec.get("P2_R6_R10_projection_execution_authorized") is False)
        gate("R6R9_third_stage_design_true", r9dec.get("P2_R6_R10_third_stage_topology_design_authorized") is True)
        gate("R6R9_support_execution_false", r9dec.get("support_growth_execution_authorized_now") is False)
        gate("R6R9_pressure_false", r9dec.get("pressure_refresh_authorized") is False)
        gate("R6R9_time_false", r9dec.get("time_advance_authorized") is False)
        gate("R6R9_P3_false", r9dec.get("P3_authorized") is False)
        r9_audit_rows = read_csv(r9dir / R6R9_AUDIT)
        r9_frozen_rows = read_csv(r9dir / R6R9_FROZEN)
        audit_unresolved = sorted(int(r["execution_group_id"]) for r in r9_audit_rows if not bool_csv(r["T2_exact_feasible"]))
        gate("R6R9_audit_unresolved_exact", audit_unresolved == EXPECTED_R6R10_INPUT, audit_unresolved)

        stage = "R7_R6_state_binding"
        r7 = drive / R7_REL
        for name in (R7_BASE, R7_TGT, R7_GRP, R7_GF, R7_MAN, R7_SUM):
            gate(f"R7_{name}_present", (r7 / name).is_file(), str(r7 / name))
        r7_manifest = read_csv(r7 / R7_MAN)
        r7_m = {r["file"]: r for r in r7_manifest}
        # Avoid re-hashing the 4.03 GB edge manifest; bind every small authority file used here.
        for name in (R7_BASE, R7_TGT, R7_GRP, R7_GF, R7_SUM):
            if name in r7_m:
                gate(f"R7_manifest_size_{name}", (r7 / name).stat().st_size == int(r7_m[name]["bytes"]))
                gate(f"R7_manifest_SHA_{name}", sha256_file(r7 / name) == r7_m[name]["sha256"])
        base_rows = read_csv(r7 / R7_BASE)
        target_rows = read_csv(r7 / R7_TGT)
        group_rows = read_csv(r7 / R7_GRP)
        gf_rows = read_csv(r7 / R7_GF)
        gate("R7_component_rows_exact", len(base_rows) == EXPECTED_COMPONENTS, len(base_rows))
        gate("R7_group_rows_exact", len(group_rows) == EXPECTED_GROUPS, len(group_rows))

        gmeta = {int(r["execution_group_id"]): r for r in group_rows}
        component_to_group: dict[int, int] = {}
        for gid, row in gmeta.items():
            for cid in [int(x) for x in row["R6R6_component_ids"].split(";") if x]:
                if cid in component_to_group:
                    raise GateError(f"duplicate_component_owner:{cid}")
                component_to_group[cid] = gid
        gate("component_partition_exact", sorted(component_to_group) == list(range(EXPECTED_COMPONENTS)))

        target_by_component = {
            cid: np.asarray(sorted(
                int(r["cv_id"]) for r in target_rows
                if int(r["component_id"]) == cid
            ), dtype=np.int64)
            for cid in range(EXPECTED_COMPONENTS)
        }

        cvrows = read_csv(drive / R6_REL / R6_CV)
        cv_to_component = {int(r["cv_id"]): int(r["component_id"]) for r in cvrows}
        component_cvs = {
            cid: np.asarray(sorted(
                cv for cv, owner in cv_to_component.items() if owner == cid
            ), dtype=np.int64)
            for cid in range(EXPECTED_COMPONENTS)
        }
        gate("all_components_nonempty", all(len(v) > 0 for v in component_cvs.values()))

        r5d = drive / R5_REL
        r5sum = load_json(r5d / R5_SUM)
        r5state = r5d / R5_STATE
        gate("R5_status_exact", r5sum.get("status") == R5_STATUS, r5sum.get("status"))
        gate("R5_state_SHA_exact", sha256_file(r5state) == R5_SHA, sha256_file(r5state))
        with np.load(r5state, allow_pickle=False) as z:
            st = {k: np.asarray(z[k]).copy() for k in z.files}

        pair_cv = np.asarray(st["existing_pair_cv"], dtype=np.int64).reshape(-1)
        pair_cell = np.asarray(st["existing_pair_cell"], dtype=np.int64).reshape(-1)
        pair_val = np.asarray(st["locally_repaired_existing_pair_contribution_kg"], dtype=np.float64).reshape(-1)
        provisional = np.asarray(st["provisional_grid_component_mass_kg"], dtype=np.float64).reshape(-1)
        r5cv = np.asarray(st["local_component_cv"], dtype=np.int64).reshape(-1)
        r5hcv = np.asarray(st["local_halo_cv"], dtype=np.int64).reshape(-1)
        r5hcell = np.asarray(st["local_halo_cell"], dtype=np.int64).reshape(-1)
        r5hmass = np.asarray(st["local_halo_contribution_kg"], dtype=np.float64).reshape(-1)
        pstate = np.asarray(st["parent_pressure_psi"], dtype=np.float64)

        d370d = drive / D370_REL
        d370sum = load_json(d370d / D370_SUM)
        gate("D370_state_present", (d370d / D370_STATE).is_file())
        gate("D370_state_SHA_exact", sha256_file(d370d / D370_STATE) == d370sum.get("accepted_state_sha256"))
        with np.load(d370d / D370_STATE, allow_pickle=False) as z:
            old = {k: np.asarray(z[k]).copy() for k in z.files}
        old_grid = np.asarray(old["grid_component_mass_kg"], dtype=np.float64).reshape(-1)
        fhcv = np.asarray(old["halo_cv"], dtype=np.int64).reshape(-1)
        fhcell = np.asarray(old["halo_cell"], dtype=np.int64).reshape(-1)
        keys = np.unique(fhcv * NCELL + fhcell)
        fhcv = (keys // NCELL).astype(np.int64)
        fhcell = (keys % NCELL).astype(np.int64)
        frozen_domain = set(int(x) for x in np.unique(fhcell).tolist())

        a2d = drive / A2E_REL
        gate("A2E_summary_present", (a2d / A2E_SUM).is_file())
        gate("A2E_epoch_present", (a2d / A2E_EPOCH).is_file())
        with np.load(a2d / A2E_EPOCH, allow_pickle=False) as z:
            ep = {k: np.asarray(z[k]).copy() for k in z.files}
        pressure = np.asarray(ep["refreshed_pressure_psi"], dtype=np.float64)
        gate("pressure_identity", float(np.max(np.abs(pressure - pstate))) <= 1e-12)

        r2 = load_module(root / R2_SOURCE, "r6r12_r2")
        pv = np.asarray(ep["pore_volume_m3"], dtype=np.float64)
        pref = scalar(ep["reference_gas_pressure_pa"])
        rho = np.asarray(
            r2.gas_density_from_state(np.full(GRID, BACKGROUND + MAX_SG), pressure, pref),
            dtype=np.float64,
        )
        capacity = (pv * rho * MAX_SG).reshape(-1)

        cur_cv = (
            np.bincount(pair_cv, weights=pair_val, minlength=NCV_TOTAL) +
            np.bincount(r5hcv, weights=r5hmass, minlength=NCV_TOTAL)
        )
        recon = (
            old_grid +
            np.bincount(pair_cell, weights=pair_val, minlength=NCELL) +
            np.bincount(r5hcell, weights=r5hmass, minlength=NCELL)
        )
        gate("provisional_reconstruct",
             float(np.max(np.abs(recon - provisional))) <= CELL_TOL_KG,
             float(np.max(np.abs(recon - provisional))))
        gate("global_mass_ledger",
             abs(float(np.sum(provisional) - (np.sum(old_grid) + np.sum(cur_cv)))) <= LEDGER_TOL_KG)

        residual = np.asarray(sorted(cv_to_component), dtype=np.int64)
        gate("residual_disjoint_R5",
             set(residual.tolist()).isdisjoint(set(r5cv.tolist())) and
             not bool(np.any(np.isin(r5hcv, residual))))

        global_s0 = set(int(x) for x in np.unique(pair_cell).tolist())
        r5_fixed = set(int(x) for x in np.unique(
            np.r_[pair_cell[np.isin(pair_cv, r5cv)], r5hcell]
        ).tolist())

        stage = "R7_compact_support_reconstruction"
        component_frontier: dict[int, set[int]] = {}
        component_baseline: dict[int, list[tuple[int, int]]] = {}
        component_cells: dict[int, set[int]] = {}
        component_targets: dict[int, set[int]] = {}

        for cid in range(EXPECTED_COMPONENTS):
            cvs = component_cvs[cid]
            tset = set(int(x) for x in target_by_component[cid].tolist())
            component_targets[cid] = tset
            s0cells = np.unique(pair_cell[np.isin(pair_cv, cvs)]).astype(np.int64)
            frontier = set(
                int(h) for h in h2xy_radius2(s0cells, global_s0)
                if int(h) in frozen_domain
            )
            component_frontier[cid] = frontier
            mask = np.isin(fhcv, cvs)
            bedges = sorted(set(
                (int(a), int(b))
                for a, b in zip(fhcv[mask].tolist(), fhcell[mask].tolist())
            ))
            component_baseline[cid] = bedges
            cc = set(int(x) for x in s0cells.tolist())
            cc.update(h for _, h in bedges)
            cc.update(frontier if tset else set())
            component_cells[cid] = cc

        # R8-R1, R6-R9 T2, R6-R10 T3, and R6-R11 T4V memberships are immutable inputs to T5AL.
        r8_extra: dict[tuple[int, int], set[int]] = {}
        for row in compact_rows:
            key = (int(row["execution_group_id"]), int(row["component_id"]))
            r8_extra.setdefault(key, set()).add(int(row["flat_cell"]))

        r9_extra: dict[tuple[int, int], set[int]] = {}
        for row in r9_frozen_rows:
            key = (int(row["execution_group_id"]), int(row["component_id"]))
            r9_extra.setdefault(key, set()).add(int(row["flat_cell"]))

        r10_extra: dict[tuple[int, int], set[int]] = {}
        for row in r10_frozen_rows:
            key = (int(row["execution_group_id"]), int(row["component_id"]))
            r10_extra.setdefault(key, set()).add(int(row["flat_cell"]))

        r11_extra: dict[tuple[int, int], set[int]] = {}
        for row in r11_frozen_rows:
            key = (int(row["execution_group_id"]), int(row["component_id"]))
            r11_extra.setdefault(key, set()).add(int(row["flat_cell"]))

        # Build current ownership including R7 + all frozen R8-R1/T2/T3/T4V support.
        current_cell_to_group: dict[int, set[int]] = {}
        for cid, cells in component_cells.items():
            gid = component_to_group[cid]
            for c in cells:
                current_cell_to_group.setdefault(int(c), set()).add(gid)
        for source in (r8_extra, r9_extra, r10_extra, r11_extra):
            for (gid, cid), cells in source.items():
                for c in cells:
                    current_cell_to_group.setdefault(int(c), set()).add(gid)

        from scipy.optimize import linprog
        from scipy import sparse

        def build_pooled(group_cids: list[int], extra: dict[int, set[int]], add_slack: bool = False):
            cvs = np.asarray(sorted(
                int(cv)
                for cid in group_cids
                for cv in component_cvs[cid].tolist()
            ), dtype=np.int64)
            pmask = np.isin(pair_cv, cvs)
            pidx = np.flatnonzero(pmask & (np.abs(pair_val) > SIGN_TOL_KG))
            xcv = pair_cv[pidx]
            xcell = pair_cell[pidx]
            x0 = pair_val[pidx]

            bindiv: list[tuple[int, int]] = []
            pools: dict[int, list[int]] = {}
            targets: dict[int, list[int]] = {}
            for cid in group_cids:
                t = sorted(component_targets[cid])
                pool = set(component_frontier[cid])
                pool.update(int(x) for x in extra.get(cid, set()))
                pools[cid] = sorted(pool)
                targets[cid] = t
                for cv, h in component_baseline[cid]:
                    if cv in component_targets[cid] and h in pool:
                        continue
                    bindiv.append((int(cv), int(h)))

            bindiv = sorted(set(bindiv))
            pcids = [cid for cid in group_cids if targets[cid]]
            ykeys = [(cid, cv) for cid in pcids for cv in targets[cid]]
            qkeys = [(cid, c) for cid in pcids for c in pools[cid]]

            nx = len(pidx)
            nb = len(bindiv)
            ny = len(ykeys)
            nq = len(qkeys)
            ncv = len(cvs)
            ox = 0
            ob = nx
            oy = ob + nb
            oq = oy + ny
            osp = oq + nq
            osm = osp + (ncv if add_slack else 0)
            nvar = osm + (ncv if add_slack else 0)

            cvrow = {int(cv): r for r, cv in enumerate(cvs.tolist())}
            prow = {cid: ncv + i for i, cid in enumerate(pcids)}
            er: list[int] = []
            ec: list[int] = []
            ev: list[float] = []

            for q, cv in enumerate(xcv.tolist()):
                er.append(cvrow[int(cv)]); ec.append(ox + q); ev.append(1.0)
            for q, (cv, c) in enumerate(bindiv):
                er.append(cvrow[cv]); ec.append(ob + q); ev.append(1.0)
            for q, (cid, cv) in enumerate(ykeys):
                er += [cvrow[cv], prow[cid]]
                ec += [oy + q, oy + q]
                ev += [1.0, 1.0]
            for q, (cid, c) in enumerate(qkeys):
                er.append(prow[cid]); ec.append(oq + q); ev.append(-1.0)
            if add_slack:
                for r in range(ncv):
                    er += [r, r]
                    ec += [osp + r, osm + r]
                    ev += [1.0, -1.0]

            Aeq = sparse.coo_matrix(
                (np.asarray(ev), (np.asarray(er), np.asarray(ec))),
                shape=(ncv + len(pcids), nvar),
            ).tocsr()
            beq = np.r_[cur_cv[cvs], np.zeros(len(pcids))]

            local_cells = set(int(x) for x in xcell.tolist())
            local_cells.update(c for _, c in bindiv)
            local_cells.update(c for _, c in qkeys)
            local = np.asarray(sorted(local_cells), dtype=np.int64)
            crow = {int(c): r for r, c in enumerate(local.tolist())}
            rr: list[int] = []
            cc: list[int] = []
            vv: list[float] = []

            for q, c in enumerate(xcell.tolist()):
                rr.append(crow[int(c)]); cc.append(ox + q); vv.append(1.0)
            for q, (cv, c) in enumerate(bindiv):
                rr.append(crow[c]); cc.append(ob + q); vv.append(1.0)
            for q, (cid, c) in enumerate(qkeys):
                rr.append(crow[c]); cc.append(oq + q); vv.append(1.0)

            Ac = sparse.coo_matrix(
                (np.asarray(vv), (np.asarray(rr), np.asarray(cc))),
                shape=(len(local), nvar),
            ).tocsr()

            fixed_delta = np.bincount(
                pair_cell[~np.isin(pair_cv, cvs)],
                weights=pair_val[~np.isin(pair_cv, cvs)],
                minlength=NCELL,
            )
            fixed = (
                old_grid +
                fixed_delta +
                np.bincount(r5hcell, weights=r5hmass, minlength=NCELL)
            )
            Aub = sparse.vstack([Ac, -Ac], format="csr")
            bub = np.r_[capacity[local] - fixed[local], fixed[local]]

            bounds: list[tuple[float | None, float | None]] = []
            for v in x0.tolist():
                if v > SIGN_TOL_KG:
                    bounds.append((0.0, None))
                elif v < -SIGN_TOL_KG:
                    bounds.append((None, 0.0))
                else:
                    bounds.append((0.0, 0.0))
            bounds += [(0.0, None)] * (nb + ny + nq + (2 * ncv if add_slack else 0))

            return {
                "cvs": cvs,
                "ncv": ncv,
                "nx": nx,
                "nb": nb,
                "ny": ny,
                "nq": nq,
                "osp": osp,
                "osm": osm,
                "nvar": nvar,
                "Aeq": Aeq,
                "beq": beq,
                "Ac": Ac,
                "Aub": Aub,
                "bub": bub,
                "bounds": bounds,
                "local": local,
                "fixed": fixed,
            }

        def solve(data: dict[str, Any], slack: bool = False):
            c = np.zeros(data["nvar"])
            if slack:
                c[data["osp"]:] = 1.0
            return linprog(
                c,
                A_ub=data["Aub"],
                b_ub=data["bub"],
                A_eq=data["Aeq"],
                b_eq=data["beq"],
                bounds=data["bounds"],
                method="highs",
                options={"presolve": True},
            )

        def metrics(data: dict[str, Any], lp: Any):
            if not lp.success:
                return False, None, None, None, None
            z = np.asarray(lp.x)
            cvres = np.asarray(
                data["Aeq"][:data["ncv"], :] @ z -
                data["beq"][:data["ncv"]]
            ).ravel()
            cm = (
                data["fixed"][data["local"]] +
                np.asarray(data["Ac"] @ z).ravel()
            )
            h = z[
                data["nx"]:
                data["nx"] + data["nb"] + data["ny"] + data["nq"]
            ]
            mcv = float(np.max(np.abs(cvres))) if len(cvres) else 0.0
            mlo = max(0.0, -float(np.min(cm))) if len(cm) else 0.0
            mhi = max(0.0, float(np.max(cm - capacity[data["local"]]))) if len(cm) else 0.0
            minh = float(np.min(h)) if len(h) else 0.0
            ok = (
                mcv <= CV_TOL_KG and
                mlo <= CELL_TOL_KG and
                mhi <= CELL_TOL_KG and
                minh >= -SIGN_TOL_KG
            )
            return ok, mcv, mlo, mhi, minh

        stage = "adjacent_layer_face_connected_lateral_topology_evaluation"
        audit_rows: list[dict[str, Any]] = []
        deficient_rows: list[dict[str, Any]] = []
        candidate_rows: list[dict[str, Any]] = []
        frozen_rows: list[dict[str, Any]] = []
        resolved_by_T5AL = 0
        still_infeasible = 0

        for gid in EXPECTED_UNRESOLVED:
            cids = [
                int(x) for x in gmeta[gid]["R6R6_component_ids"].split(";") if x
            ]

            # Complete frozen support at entry: T1B + T2 + T3 + T4V.
            base_extra: dict[int, set[int]] = {}
            for cid in cids:
                base_extra[cid] = set(r8_extra.get((gid, cid), set()))
                base_extra[cid].update(r9_extra.get((gid, cid), set()))
                base_extra[cid].update(r10_extra.get((gid, cid), set()))
                base_extra[cid].update(r11_extra.get((gid, cid), set()))

            # Reproduce formal R6-R11 T4V insufficiency under identical pooled semantics.
            base = build_pooled(cids, base_extra, False)
            lp_base = solve(base, False)
            ok_base, *_ = metrics(base, lp_base)
            gate(f"group_{gid}_R6R11_T4V_infeasible_reproduced", not ok_base, lp_base.message)

            # Re-localize remaining conservation deficit after complete T4V support.
            slack_data = build_pooled(cids, base_extra, True)
            lp_slack = solve(slack_data, True)
            gate(f"group_{gid}_post_T4V_slack_LP_success", lp_slack.success, lp_slack.message)

            z = np.asarray(lp_slack.x)
            n = slack_data["ncv"]
            sp = z[slack_data["osp"]:slack_data["osp"] + n]
            sm = z[slack_data["osm"]:slack_data["osm"] + n]
            abs_slack = sp + sm
            signed_slack = sp - sm
            total_slack = float(np.sum(abs_slack))
            max_slack = float(np.max(abs_slack))
            total_tol = max(
                SLACK_TOTAL_ABS_TOL_KG,
                abs(float(np.sum(cur_cv[slack_data["cvs"]]))) * SLACK_TOTAL_REL_TOL,
            )
            gate(f"group_{gid}_post_T4V_nonzero_slack", total_slack > total_tol, total_slack)

            mask = abs_slack > SLACK_CV_TOL_KG
            dcvs = slack_data["cvs"][mask]
            gate(f"group_{gid}_post_T4V_deficient_CVs", len(dcvs) > 0, len(dcvs))
            dcomps = sorted(set(cv_to_component[int(cv)] for cv in dcvs.tolist()))

            for cv, a, ss in zip(
                dcvs.tolist(), abs_slack[mask].tolist(), signed_slack[mask].tolist()
            ):
                deficient_rows.append({
                    "execution_group_id": gid,
                    "component_id": cv_to_component[int(cv)],
                    "cv_id": int(cv),
                    "streamline": int(cv // NCV),
                    "cv_node": int(cv % NCV),
                    "post_T4V_minimum_L1_absolute_conservation_slack_kg": float(a),
                    "post_T4V_signed_conservation_slack_kg": float(ss),
                })

            fixed = slack_data["fixed"]
            t5al_extra = {cid: set(base_extra[cid]) for cid in cids}
            t5al_candidate_count = 0
            t5al_new_endpoint_count = 0
            t5al_anchor_count = 0

            for cid in cids:
                if cid not in dcomps:
                    continue

                current = set(component_cells[cid])
                current.update(base_extra[cid])
                anchors = set(r11_extra.get((gid, cid), set()))
                t5al_anchor_count += len(anchors)

                # T5AL is one XY face step from a frozen T4V vertical endpoint.
                # The anchor is a geometric witness only: no anchor-to-lateral
                # mass transit variable is introduced. Target CVs deposit directly
                # to the new terminal endpoint under the existing pooled semantics.
                witness_map: dict[int, set[int]] = {}
                for anchor in anchors:
                    for c in adjacent_layer_lateral_neighbors({int(anchor)}):
                        c = int(c)
                        if c in current:
                            continue
                        witness_map.setdefault(c, set()).add(int(anchor))

                shell = set(witness_map)
                shell = {
                    int(c) for c in shell
                    if int(c) not in global_s0 and int(c) not in r5_fixed
                }
                shell = {
                    int(c) for c in shell
                    if all(owner == gid for owner in current_cell_to_group.get(int(c), {gid}))
                }
                shell = {
                    int(c) for c in shell
                    if capacity[int(c)] - fixed[int(c)] > POSITIVE_ROOM_TOL_KG
                }

                t5al_extra[cid].update(shell)
                t5al_candidate_count += len(shell)
                t5al_new_endpoint_count += sum(1 for c in shell if c not in frozen_domain)

                for c in sorted(shell):
                    k, j, i = ijk(c)
                    witnesses = sorted(witness_map[c])
                    candidate_rows.append({
                        "execution_group_id": gid,
                        "component_id": cid,
                        "tier": "T5AL_ADJACENT_LAYER_FACE_CONNECTED_LATERAL",
                        "flat_cell": c,
                        "k": k,
                        "j": j,
                        "i": i,
                        "vertical_anchor_cell_count": len(witnesses),
                        "vertical_anchor_cells": ";".join(map(str, witnesses)),
                        "already_in_Day370_frozen_H2_domain": c in frozen_domain,
                        "new_H2_endpoint_cell_if_executed": c not in frozen_domain,
                        "same_layer_relative_to_vertical_anchor": True,
                        "adjacent_layer_relative_to_pre_T4V_support": True,
                        "face_connected_to_frozen_vertical_anchor": True,
                        "vertical": False,
                        "diagonal": False,
                        "adjacent_layer_lateral": True,
                        "vertical_anchor_is_transit_node": False,
                        "terminal_sink_only": True,
                        "halo_transit": False,
                        "cross_group_overlap_allowed": False,
                        "fixed_external_room_kg": float(capacity[c] - fixed[c]),
                    })

            t5al = build_pooled(cids, t5al_extra, False)
            lp_t5al = solve(t5al, False)
            ok_t5al, mcv, mlo, mhi, minh = metrics(t5al, lp_t5al)

            if ok_t5al:
                resolved_by_T5AL += 1
                support_class = "T5AL_ADJACENT_LAYER_FACE_CONNECTED_LATERAL_EXACT_FEASIBLE"
            else:
                still_infeasible += 1
                support_class = "T5AL_ADJACENT_LAYER_FACE_CONNECTED_LATERAL_INSUFFICIENT"

            for cid in cids:
                for c in sorted(t5al_extra[cid]):
                    if c in base_extra[cid]:
                        continue
                    k, j, i = ijk(c)
                    frozen_rows.append({
                        "execution_group_id": gid,
                        "component_id": cid,
                        "support_class": support_class,
                        "flat_cell": c,
                        "k": k,
                        "j": j,
                        "i": i,
                        "cell_in_Day370_frozen_H2_domain": c in frozen_domain,
                        "new_H2_endpoint_if_executed": c not in frozen_domain,
                        "complete_bipartite_rule": (
                            "all_R6R7_target_CVs_in_this_component_may_deposit_"
                            "nonnegative_mass_directly_to_this_adjacent_layer_lateral_terminal_sink"
                        ),
                        "face_connected_to_frozen_vertical_anchor": True,
                        "vertical_anchor_is_transit_node": False,
                        "terminal_sink_only": True,
                        "adjacent_layer_lateral": True,
                        "halo_transit": False,
                    })

            audit_rows.append({
                "execution_group_id": gid,
                "R6R6_component_ids": ";".join(map(str, cids)),
                "component_count": len(cids),
                "post_T4V_deficient_CV_count": len(dcvs),
                "post_T4V_deficient_component_count": len(dcomps),
                "post_T4V_deficient_component_ids": ";".join(map(str, dcomps)),
                "post_T4V_minimum_L1_total_absolute_conservation_slack_kg": total_slack,
                "post_T4V_minimum_L1_max_absolute_conservation_slack_kg": max_slack,
                "T5AL_vertical_anchor_membership_count": t5al_anchor_count,
                "T5AL_candidate_cell_membership_count": t5al_candidate_count,
                "T5AL_new_endpoint_cell_membership_count": t5al_new_endpoint_count,
                "T5AL_exact_feasible": bool(ok_t5al),
                "HiGHS_status": int(lp_t5al.status),
                "HiGHS_message": str(lp_t5al.message),
                "maximum_CV_residual_kg": mcv,
                "maximum_cell_lower_violation_kg": mlo,
                "maximum_cell_upper_violation_kg": mhi,
                "minimum_H2_variable_kg": minh,
                "support_class": support_class,
            })

        gate(
            "five_group_partition",
            resolved_by_T5AL + still_infeasible == len(EXPECTED_UNRESOLVED),
            (resolved_by_T5AL, still_infeasible),
        )

        stage = "artifact_publication"
        out.mkdir(parents=True, exist_ok=False)

        audit_path = out / "POSTV16_AV4_PIVOT_P2_R6_R12_AdjacentLayerLateral_Exact_Feasibility_Audit.csv"
        deficient_path = out / "POSTV16_AV4_PIVOT_P2_R6_R12_PostT4V_Localized_Deficient_CVs.csv"
        candidate_path = out / "POSTV16_AV4_PIVOT_P2_R6_R12_AdjacentLayerLateral_Candidate_Terminal_Sinks.csv"
        frozen_path = out / "POSTV16_AV4_PIVOT_P2_R6_R12_Frozen_AdjacentLayerLateral_Support_Extension.csv"

        audit_path.write_bytes(csv_bytes(audit_rows))
        deficient_path.write_bytes(csv_bytes(deficient_rows))
        candidate_path.write_bytes(csv_bytes(candidate_rows))
        frozen_path.write_bytes(csv_bytes(frozen_rows))

        all_resolved = still_infeasible == 0
        if all_resolved:
            classification = (
                "R6R12_ADJACENT_LAYER_FACE_CONNECTED_LATERAL_RESOLVES_ALL_5_"
                "CONTROLLED_3D_PROJECTION_EXECUTION_NEXT"
            )
            next_name = (
                "Controlled Day375 Residual 3D Minimal-Support Exact "
                "CV-Conservative Projection Execution"
            )
            next_exec = True
            next_design = False
        else:
            classification = (
                "R6R12_ADJACENT_LAYER_FACE_CONNECTED_LATERAL_INSUFFICIENT_"
                "RESIDUAL_GROUPS_REQUIRE_COMPONENT_SPECIFIC_LOCAL_3D_SUPPORT_ENVELOPE_DESIGN"
            )
            next_name = (
                "Day375 Residual Component-Specific Local 3D Face-Connected "
                "Support Envelope Design Freeze"
            )
            next_exec = False
            next_design = True

        unresolved_after_t5al = [
            int(r["execution_group_id"])
            for r in audit_rows
            if not bool(r["T5AL_exact_feasible"])
        ]

        contract = {
            "milestone": MILESTONE,
            "name": MILESTONE_NAME,
            "status": STATUS_PASS,
            "classification": classification,
            "design_freeze_only": True,
            "state_mutation_executed": False,
            "authority": {
                "R6R11_parent_commit": EXPECTED_PARENT,
                "R6R11_status": R6R11_STATUS,
                "R6R11_classification": R6R11_CLASS,
                "R6R11_unresolved_after_T4V_group_ids": EXPECTED_UNRESOLVED,
                "R8R1_scientific_summary_sha256": R8R1_SUM_SHA,
                "R8R1_scientific_decision_sha256": R8R1_DEC_SHA,
            },
            "T5AL_topology_semantics": {
                "scope": "only the five R6-R11 unresolved execution groups",
                "relocalization_basis": (
                    "minimum-L1 CV conservation slack after complete frozen "
                    "R8-R1 T1B plus R6-R9 T2 plus R6-R10 T3 plus R6-R11 T4V support"
                ),
                "geometry": (
                    "one same-k XY face step from frozen R6-R11 T4V vertical support "
                    "cells; therefore each new endpoint is face-connected in an adjacent layer"
                ),
                "vertical_anchor_semantics": (
                    "geometric witness only; no anchor-to-lateral transit variable and no halo transit"
                ),
                "geometric_depth": "one lateral face step from an already-frozen T4V vertical endpoint",
                "additional_vertical_expansion": False,
                "recursive_adjacent_layer_lateral_expansion": False,
                "diagonal_support": False,
                "terminal_sink_only": True,
                "global_S0_excluded": True,
                "R5_local_footprint_excluded": True,
                "other_group_current_support_excluded": True,
                "cross_group_overlap_allowed": False,
                "positive_fixed_external_room_required": True,
                "capacity_semantics": "exact Day365-pressure physical gas capacity",
                "R8R1_support_immutable": True,
                "R6R9_T2_support_immutable": True,
                "R6R10_T3_support_immutable": True,
                "R6R11_T4V_support_immutable": True,
                "R5_local_repair_immutable": True,
            },
            "scientific_result": {
                "input_unresolved_group_count": len(EXPECTED_UNRESOLVED),
                "T5AL_exact_feasible_group_count": resolved_by_T5AL,
                "T5AL_still_infeasible_group_count": still_infeasible,
                "unresolved_after_T5AL_group_ids": unresolved_after_t5al,
                "post_T4V_localized_deficient_CV_count": len(deficient_rows),
                "T5AL_candidate_terminal_sink_membership_count": len(candidate_rows),
                "T5AL_frozen_support_membership_count": len(frozen_rows),
            },
            "successor": {
                "P2_R6_R13_authorized": True,
                "P2_R6_R13_name": next_name,
                "P2_R6_R13_projection_execution_authorized": next_exec,
                "P2_R6_R13_local_3d_support_envelope_design_authorized": next_design,
                "current_support_growth_execution_authorized": False,
                "current_new_H2_endpoint_execution_authorized": False,
                "pressure_refresh_authorized": False,
                "time_advance_authorized": False,
                "P3_authorized": False,
                "P4_authorized": False,
                "P5_training_authorized": False,
            },
        }

        summary = {
            "milestone": MILESTONE,
            "name": MILESTONE_NAME,
            "status": STATUS_PASS,
            "classification": classification,
            "design_freeze_only": True,
            "state_mutation_executed": False,
            "accepted_Day375_state_created": False,
            "input_unresolved_group_ids": EXPECTED_UNRESOLVED,
            "input_unresolved_group_count": len(EXPECTED_UNRESOLVED),
            "T5AL_exact_feasible_group_count": resolved_by_T5AL,
            "T5AL_still_infeasible_group_count": still_infeasible,
            "unresolved_after_T5AL_group_ids": unresolved_after_t5al,
            "post_T4V_localized_deficient_CV_count": len(deficient_rows),
            "T5AL_candidate_terminal_sink_membership_count": len(candidate_rows),
            "T5AL_frozen_support_membership_count": len(frozen_rows),
            "all_5_resolved_by_adjacent_layer_face_connected_lateral_support": all_resolved,
            "R8R1_support_held_fixed": True,
            "R6R9_T2_support_held_fixed": True,
            "R6R10_T3_support_held_fixed": True,
            "R6R11_T4V_support_held_fixed": True,
            "R5_local_repair_held_fixed": True,
            "new_H2_endpoint_execution_performed": False,
            "vertical_support_used": True,
            "vertical_support_executed": False,
            "adjacent_layer_lateral_support_used": True,
            "adjacent_layer_lateral_support_executed": False,
            "vertical_anchor_transit_used": False,
            "diagonal_support_used": False,
            "halo_transit_used": False,
            "pressure_refresh_executed": False,
            "time_advance_executed": False,
            "P3_authorized": False,
            "P4_authorized": False,
            "P5_training_authorized": False,
        }

        decision = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "classification": classification,
            "P2_R6_R13_authorized": True,
            "P2_R6_R13_name": next_name,
            "P2_R6_R13_projection_execution_authorized": next_exec,
            "P2_R6_R13_local_3d_support_envelope_design_authorized": next_design,
            "P2_R6_R13_must_bind_R6R8R1_compact_support_contract": True,
            "P2_R6_R13_must_bind_R6R9_second_stage_support_contract": True,
            "P2_R6_R13_must_bind_R6R10_third_stage_support_contract": True,
            "P2_R6_R13_must_bind_R6R11_vertical_support_contract": True,
            "P2_R6_R13_must_bind_R6R12_adjacent_layer_lateral_support_contract": True,
            "P2_continuation_restart_authorized_now": False,
            "accepted_Day375_state_authorized_now": False,
            "support_growth_execution_authorized_now": False,
            "new_H2_endpoint_execution_authorized_now": False,
            "pressure_refresh_authorized": False,
            "Darcy_Pollock_TOF_regeneration_authorized": False,
            "time_advance_authorized": False,
            "P3_authorized": False,
            "P4_authorized": False,
            "P5_training_authorized": False,
        }

        contract_path = out / "POSTV16_AV4_PIVOT_P2_R6_R12_AdjacentLayerLateral_Topology_Design_Contract.json"
        summary_path = out / "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R12_Summary.json"
        decision_path = out / "POSTV16_AV4_PIVOT_P2_R6_R12_Decision_Contract.json"
        contract_path.write_bytes(json_bytes(contract))
        summary_path.write_bytes(json_bytes(summary))
        decision_path.write_bytes(json_bytes(decision))

        gate("R5_state_SHA_unchanged_after_R6R12", sha256_file(r5state) == R5_SHA, sha256_file(r5state))

        gate_path = out / "POSTV16_AV4_PIVOT_P2_R6_R12_Final_Gate_Matrix.csv"
        gate_path.write_bytes(csv_bytes(gates))

        manifest_rows: list[dict[str, Any]] = []
        for fp in sorted(out.iterdir()):
            if fp.is_file():
                manifest_rows.append({
                    "file": fp.name,
                    "sha256": sha256_file(fp),
                    "bytes": fp.stat().st_size,
                })
        (out / "POSTV16_AV4_PIVOT_P2_R6_R12_Artifact_Manifest.csv").write_bytes(
            csv_bytes(manifest_rows)
        )

        print()
        print("=" * 216)
        print("POSTV16-AV4-PIVOT-P2-R6-R12: PASS")
        print("Input unresolved groups                         :", EXPECTED_UNRESOLVED)
        print("T5AL exact-feasible groups                     :", resolved_by_T5AL)
        print("Still infeasible after T5AL                    :", still_infeasible)
        print("Unresolved after T5AL                          :", unresolved_after_t5al)
        print("Post-T4V localized deficient CVs               :", len(deficient_rows))
        print("T5AL adjacent-layer lateral memberships        :", len(candidate_rows))
        print("T5AL frozen support memberships                :", len(frozen_rows))
        print("R6-R13 projection execution authorized         :", next_exec)
        print("R6-R13 local-3D envelope design authorized     :", next_design)
        print("Day375 state mutation                          : False")
        print("Pressure refresh                               : False")
        print("Time advance                                   : False")
        print("P3 authorized                                  : False")
        print("=" * 216)
        return 0

    except Exception as exc:
        block.mkdir(parents=True, exist_ok=True)
        rp = block / "POSTV16_AV4_PIVOT_P2_R6_R12_Blocked_Report.json"
        if not rp.exists():
            rp.write_text(
                json.dumps({
                    "milestone": MILESTONE,
                    "status": STATUS_BLOCK,
                    "failed_stage": stage,
                    "exception": repr(exc),
                    "state_mutation_executed": False,
                    "support_growth_execution_authorized": False,
                    "new_H2_endpoint_execution_authorized": False,
                    "pressure_refresh_authorized": False,
                    "time_advance_authorized": False,
                    "P3_authorized": False,
                    "P4_authorized": False,
                    "P5_training_authorized": False,
                    "automatic_rerun_authorized": False,
                    "gates_completed": gates,
                }, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        print(MILESTONE + ": BLOCKED")
        print("Stage:", stage)
        print("Exception:", repr(exc))
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
