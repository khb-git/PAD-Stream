#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import subprocess
from pathlib import Path
from typing import Any

import numpy as np

M = "POSTV16-AV4-PIVOT-P2-R6-R21-R4-R1-R3"
NAME = "Historical Parent-State CV/Grid Provenance Match Diagnostic"

PASS = "AV4PIVOTP2R6R21R4R1R3_HISTORICAL_PARENTSTATE_PROVENANCE_MATCH_DIAGNOSTIC_PASS_NO_STATE_MUTATION"
BLOCK = "AV4PIVOTP2R6R21R4R1R3_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "051deaeb2ad4cc6bf95ee0913ca8721a3b20cd94"

R4R1R2_RUNNER = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R2_Day370_RepairedLedger_CVCell_Provenance_Recovery_Diagnostic.py"
R4R1R2_BLOB = "015b903dbcc43d053a0f2e076fc00249a443f383"
R19_RUNNER = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R19_Controlled_Remaining_Group_Coupled_Global_Reconciliation_Execution.py"
R19_BLOB = "2626e4a08660a907752be5aca70d29f69dd2a71e"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

D370 = BASE / (
    "POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_R1_"
    "CompletedComponent_CellMembership_Identity_Repair_and_Controlled_Projection"
)
R20 = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R20_Day375_Globally_Reconciled_"
    "Provisional_State_Closure_and_Acceptance_Audit"
)
R4R1R2 = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R2_"
    "Day370_RepairedLedger_CVCell_Provenance_Recovery_Diagnostic"
)

D370_STATE = "POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_R1_Repaired_Day370_State.npz"
R20_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R20_Summary.json"
R20_ACCEPTANCE = "POSTV16_AV4_PIVOT_P2_R6_R20_Day375_State_Acceptance_Contract.json"
R20_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R20_Artifact_Manifest.csv"
R4R1R2_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R2_Summary.json"
R4R1R2_DECISION = "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R2_Decision_Contract.json"
R4R1R2_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R2_Artifact_Manifest.csv"

OUT = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R3_"
    "Historical_ParentState_Provenance_Match_Diagnostic"
)
BLK = BASE / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R3_BLOCKED"

NCELL = 37500
TOL = 1e-7
DAY_MAX = 370.0 + 1e-12

GRID_KEYS = (
    "grid_component_mass_kg",
    "provisional_grid_component_mass_kg",
    "parent_component_mass_kg",
)
CV_KEYS = (
    "cv_component_mass_kg",
    "preserved_CV_mass_kg",
)
DAY_KEYS = ("day", "state_day", "canonical_day", "current_day", "target_day")


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


def scalar_day(z: Any) -> float | None:
    for key in DAY_KEYS:
        if key in z.files:
            try:
                arr = np.asarray(z[key])
                if arr.size == 1:
                    val = float(arr.reshape(()))
                    if np.isfinite(val):
                        return val
            except Exception:
                pass
    return None


def metric(candidate: np.ndarray, target: np.ndarray) -> tuple[float, float]:
    a = np.asarray(candidate, dtype=float).reshape(-1)
    b = np.asarray(target, dtype=float).reshape(-1)
    if a.shape != b.shape:
        return float("inf"), float("inf")
    d = np.abs(a - b)
    return float(np.max(d)), float(np.sum(d))


def selftest() -> None:
    a = np.asarray([1.0, 2.0])
    b = np.asarray([1.0, 2.5])
    m, l1 = metric(a, b)
    assert abs(m - 0.5) < 1e-12
    assert abs(l1 - 0.5) < 1e-12
    print("POSTV16 AV4 PIVOT P2-R6-R21-R4-R1-R3 structural self-test: PASS")


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
        summary_path = out / "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R3_Summary.json"
        block_path = block / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R3_Blocked_Report.json"
        if summary_path.is_file():
            print("[PASS] formal R6-R21-R4-R1-R3 PASS already exists; immutable outcome preserved.")
            return 0
        gate("no_preexisting_R6R21R4R1R3_BLOCK", not block_path.exists())

        stage = "repository_authority"
        gate("branch_exact", gt(root, "branch", "--show-current") == BRANCH)
        gate("parent_is_R6R21R4R1R2", gt(root, "rev-parse", "HEAD^") == PARENT)
        gate("repository_clean", gt(root, "status", "--porcelain") == "")
        gate("R4R1R2_runner_blob_exact", gt(root, "hash-object", str(root / R4R1R2_RUNNER)) == R4R1R2_BLOB)
        gate("R19_runner_blob_exact", gt(root, "hash-object", str(root / R19_RUNNER)) == R19_BLOB)

        stage = "R4R1R2_authority"
        r412 = drive / R4R1R2
        manifest(r412, R4R1R2_MANIFEST)
        s412 = js(r412 / R4R1R2_SUMMARY)
        d412 = js(r412 / R4R1R2_DECISION)

        gate(
            "R4R1R2_status_exact",
            s412.get("status") ==
            "AV4PIVOTP2R6R21R4R1R2_DAY370_REPAIRED_LEDGER_CVCELL_PROVENANCE_RECOVERY_DIAGNOSTIC_PASS_NO_STATE_MUTATION",
        )
        gate("R4R1R3_authorized", d412.get("P2_R6_R21_R4_R1_R3_authorized") is True)
        gate("R4R1R2_full_provenance_false", s412.get("full_Day370_CV_cell_provenance_recovered") is False)
        gate(
            "R4R1R2_all_9_sources_have_positive_CV_availability",
            int(s412["source_cells_with_positive_CV_availability_shortfall_after_recovery"]) == 0,
        )
        gate("R4R1R2_no_state_mutation", s412.get("state_mutation_executed") is False)

        stage = "accepted_state_authority"
        r20 = drive / R20
        manifest(r20, R20_MANIFEST)
        s20 = js(r20 / R20_SUMMARY)
        a20 = js(r20 / R20_ACCEPTANCE)
        accepted_sha = str(a20["accepted_Day375_state_sha256"])
        gate("R20_accepted_state_true", a20.get("accepted_Day375_state") is True)
        gate("accepted_SHA_matches_summary", accepted_sha == s20["accepted_Day375_state_sha256"])

        stage = "Day370_residual_construction"
        d370_path = drive / D370 / D370_STATE
        gate("Day370_state_present", d370_path.is_file(), str(d370_path))
        d370_sha = sha(d370_path)

        with np.load(d370_path, allow_pickle=False) as z:
            required = [
                "cv_component_mass_kg",
                "grid_component_mass_kg",
                "existing_pair_cv",
                "existing_pair_cell",
                "repaired_existing_pair_contribution_kg",
                "halo_cv",
                "halo_cell",
                "repaired_halo_contribution_kg",
            ]
            missing = [k for k in required if k not in z.files]
            gate("Day370_required_fields_present", not missing, missing)

            cv_mass = np.asarray(z["cv_component_mass_kg"], dtype=float).reshape(-1)
            grid_mass = np.asarray(z["grid_component_mass_kg"], dtype=float).reshape(-1)
            pair_cv = np.asarray(z["existing_pair_cv"], dtype=np.int64).reshape(-1)
            pair_cell = np.asarray(z["existing_pair_cell"], dtype=np.int64).reshape(-1)
            pair_mass = np.asarray(z["repaired_existing_pair_contribution_kg"], dtype=float).reshape(-1)
            halo_cv = np.asarray(z["halo_cv"], dtype=np.int64).reshape(-1)
            halo_cell = np.asarray(z["halo_cell"], dtype=np.int64).reshape(-1)
            halo_mass = np.asarray(z["repaired_halo_contribution_kg"], dtype=float).reshape(-1)

        ledger_grid = (
            np.bincount(pair_cell, weights=pair_mass, minlength=NCELL)
            + np.bincount(halo_cell, weights=halo_mass, minlength=NCELL)
        )
        ledger_cv = (
            np.bincount(pair_cv, weights=pair_mass, minlength=cv_mass.size)
            + np.bincount(halo_cv, weights=halo_mass, minlength=cv_mass.size)
        )
        residual_grid = grid_mass - ledger_grid
        residual_cv = cv_mass - ledger_cv

        gate(
            "residual_grid_matches_R4R1R2_max_error",
            abs(float(np.max(np.abs(residual_grid))) - float(s412["maximum_unattributed_cartesian_residual_kg"])) <= 1e-7,
        )

        stage = "historical_NPZ_parent_search"
        base_dir = drive / BASE
        gate("dynamic_flow_coupling_base_present", base_dir.is_dir(), str(base_dir))

        candidates = []
        scanned = 0
        load_errors = 0

        for path in sorted(base_dir.rglob("*.npz")):
            rel = str(path.relative_to(base_dir)).replace("\\", "/")

            # Exclude the state being decomposed and all R6-R21 diagnostic/repair descendants.
            if path.resolve() == d370_path.resolve():
                continue
            if "POSTV16_AV4_PIVOT_P2_R6_R21_" in rel:
                continue

            scanned += 1
            if scanned > 600:
                break

            try:
                with np.load(path, allow_pickle=False) as z:
                    day = scalar_day(z)
                    grid_matches = []
                    cv_matches = []

                    for key in GRID_KEYS:
                        if key not in z.files:
                            continue
                        arr = np.asarray(z[key])
                        if arr.size != residual_grid.size:
                            continue
                        mx, l1 = metric(arr, residual_grid)
                        grid_matches.append((key, mx, l1))

                    for key in CV_KEYS:
                        if key not in z.files:
                            continue
                        arr = np.asarray(z[key])
                        if arr.size != residual_cv.size:
                            continue
                        mx, l1 = metric(arr, residual_cv)
                        cv_matches.append((key, mx, l1))

                    if not grid_matches and not cv_matches:
                        continue

                    best_g = min(grid_matches, key=lambda x: (x[1], x[2])) if grid_matches else None
                    best_c = min(cv_matches, key=lambda x: (x[1], x[2])) if cv_matches else None

                    exact_g = bool(best_g is not None and best_g[1] <= TOL)
                    exact_c = bool(best_c is not None and best_c[1] <= TOL)
                    day_authoritative = bool(day is None or day <= DAY_MAX)

                    candidates.append({
                        "relative_path": rel,
                        "file_sha256": sha(path),
                        "bytes": path.stat().st_size,
                        "day": day,
                        "day_at_or_before_370_or_unknown": day_authoritative,
                        "best_grid_key": None if best_g is None else best_g[0],
                        "best_grid_max_abs_error_kg": None if best_g is None else best_g[1],
                        "best_grid_L1_error_kg": None if best_g is None else best_g[2],
                        "exact_residual_grid_match": exact_g,
                        "best_CV_key": None if best_c is None else best_c[0],
                        "best_CV_max_abs_error_kg": None if best_c is None else best_c[1],
                        "best_CV_L1_error_kg": None if best_c is None else best_c[2],
                        "exact_residual_CV_match": exact_c,
                        "exact_joint_parent_match": bool(exact_g and exact_c and day_authoritative),
                    })

            except Exception:
                load_errors += 1

        gate("historical_NPZ_scan_completed", scanned > 0, scanned)

        candidates.sort(
            key=lambda r: (
                not bool(r["exact_joint_parent_match"]),
                not bool(r["exact_residual_grid_match"]),
                not bool(r["exact_residual_CV_match"]),
                float("inf") if r["best_grid_max_abs_error_kg"] is None else float(r["best_grid_max_abs_error_kg"]),
                float("inf") if r["best_CV_max_abs_error_kg"] is None else float(r["best_CV_max_abs_error_kg"]),
                r["relative_path"],
            )
        )

        exact_joint = [r for r in candidates if r["exact_joint_parent_match"]]
        exact_grid = [r for r in candidates if r["exact_residual_grid_match"] and r["day_at_or_before_370_or_unknown"]]
        exact_cv = [r for r in candidates if r["exact_residual_CV_match"] and r["day_at_or_before_370_or_unknown"]]

        stage = "parent_provenance_classification"
        if exact_joint:
            selected = exact_joint[0]
            classification = (
                "R6R21R4R1R3_EXACT_HISTORICAL_PARENT_STATE_MATCH_RECOVERED_"
                "FULL_DAY370_PROVENANCE_CHAIN_SEMANTICS_FREEZE_NEXT"
            )
            next_name = (
                "Recovered Full Day370 Parent+Repair CV-Cell Provenance "
                "Pressure-Capacity Reconciliation Semantics Design Freeze"
            )
            provenance_state = "EXACT_JOINT_PARENT_STATE_RECOVERED"
        elif exact_grid and exact_cv:
            selected = None
            classification = (
                "R6R21R4R1R3_GRID_AND_CV_PARENT_COMPONENTS_RECOVERED_FROM_DISTINCT_"
                "HISTORICAL_ARTIFACTS_CROSS_ARTIFACT_BINDING_DIAGNOSTIC_NEXT"
            )
            next_name = "Day370 Cross-Artifact Parent Provenance Binding Diagnostic"
            provenance_state = "DISTINCT_EXACT_GRID_AND_CV_SOURCES_FOUND"
        elif exact_grid or exact_cv:
            selected = None
            classification = (
                "R6R21R4R1R3_PARTIAL_PARENT_STATE_MATCH_RECOVERED_"
                "MISSING_COMPONENT_PROVENANCE_DIAGNOSTIC_NEXT"
            )
            next_name = "Day370 Missing Parent-State Provenance Component Diagnostic"
            provenance_state = "PARTIAL_EXACT_PARENT_MATCH"
        else:
            selected = None
            classification = (
                "R6R21R4R1R3_NO_EXACT_PARENT_STATE_MATCH_IN_FROZEN_DYNAMIC_FLOW_ARTIFACTS_"
                "DEEPER_LINEAGE_RECOVERY_DIAGNOSTIC_NEXT"
            )
            next_name = "Day370 Deeper Lineage / Pre-Dynamic-Flow Provenance Recovery Diagnostic"
            provenance_state = "NO_EXACT_PARENT_MATCH"

        diagnostic = {
            "accepted_Day375_state_sha256": accepted_sha,
            "Day370_state_sha256": d370_sha,
            "residual_grid_max_abs_kg": float(np.max(np.abs(residual_grid))),
            "residual_grid_L1_kg": float(np.sum(np.abs(residual_grid))),
            "residual_grid_net_kg": float(np.sum(residual_grid)),
            "residual_CV_max_abs_kg": float(np.max(np.abs(residual_cv))),
            "residual_CV_L1_kg": float(np.sum(np.abs(residual_cv))),
            "residual_CV_net_kg": float(np.sum(residual_cv)),
            "historical_NPZ_files_scanned": scanned,
            "historical_NPZ_load_errors": load_errors,
            "candidate_files_with_comparable_arrays": len(candidates),
            "exact_joint_parent_match_count": len(exact_joint),
            "exact_residual_grid_match_count": len(exact_grid),
            "exact_residual_CV_match_count": len(exact_cv),
            "parent_provenance_recovery_state": provenance_state,
            "selected_exact_joint_parent": selected,
            "all_9_pressure_source_cells_have_positive_repaired_CV_availability": True,
            "accepted_transport_state_invalidated": False,
            "state_mutation_executed": False,
            "pressure_refresh_accepted": False,
        }

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": classification,
            **diagnostic,
            "Darcy_Pollock_TOF_regeneration_executed": False,
            "time_advance_executed": False,
            "P3_authorized": False,
        }

        decision = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "P2_R6_R21_R4_R1_R4_authorized": True,
            "P2_R6_R21_R4_R1_R4_name": next_name,
            "P2_R6_R21_R4_R1_R4_design_or_diagnostic_only": True,
            "parent_provenance_recovery_state": provenance_state,
            "exact_joint_parent_state_recovered": bool(exact_joint),
            "accepted_Day375_transport_state_remains_authoritative": True,
            "pressure_reconciliation_execution_authorized_now": False,
            "support_growth_execution_authorized_now": False,
            "Darcy_Pollock_TOF_regeneration_authorized": False,
            "time_advance_authorized": False,
            "P3_authorized": False,
            "P4_authorized": False,
            "P5_training_authorized": False,
        }

        stage = "artifact_publication"
        out.mkdir(parents=True, exist_ok=False)
        (out / "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R3_Summary.json").write_bytes(jb(summary))
        (out / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R3_Parent_State_Match_Audit.csv").write_bytes(
            csvb(candidates[:200])
        )
        (out / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R3_Diagnostic_Contract.json").write_bytes(jb(diagnostic))
        (out / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R3_Decision_Contract.json").write_bytes(jb(decision))
        (out / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R3_Final_Gate_Matrix.csv").write_bytes(csvb(gates))

        manifest_rows = []
        for p in sorted(out.iterdir()):
            if p.is_file():
                manifest_rows.append({
                    "file": p.name,
                    "sha256": sha(p),
                    "bytes": p.stat().st_size,
                })
        (out / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R3_Artifact_Manifest.csv").write_bytes(csvb(manifest_rows))

        print("=" * 190)
        print(M, "PASS")
        print("Accepted Day375 state SHA256              :", accepted_sha)
        print("Day370 state SHA256                       :", d370_sha)
        print("Residual grid max / L1 kg                 :", float(np.max(np.abs(residual_grid))), "/", float(np.sum(np.abs(residual_grid))))
        print("Residual CV max / L1 kg                   :", float(np.max(np.abs(residual_cv))), "/", float(np.sum(np.abs(residual_cv))))
        print("Historical NPZ files scanned              :", scanned)
        print("Comparable candidate files                :", len(candidates))
        print("Exact joint parent matches                :", len(exact_joint))
        print("Exact grid parent matches                 :", len(exact_grid))
        print("Exact CV parent matches                   :", len(exact_cv))
        print("Parent provenance recovery state          :", provenance_state)
        if selected is not None:
            print("Selected exact parent path                :", selected["relative_path"])
            print("Selected exact parent SHA256              :", selected["file_sha256"])
            print("Selected exact parent day                 :", selected["day"])
            print("Selected grid / CV keys                   :", selected["best_grid_key"], "/", selected["best_CV_key"])
        print("State mutation / pressure acceptance      : False / False")
        print("R4-R1-R4 design/diagnostic authorized     : True")
        print("Darcy/Pollock/TOF / time / P3             : False / False / False")
        print("=" * 190)
        return 0

    except Exception as exc:
        block.mkdir(parents=True, exist_ok=True)
        p = block / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R3_Blocked_Report.json"
        if not p.exists():
            p.write_bytes(jb({
                "milestone": M,
                "status": BLOCK,
                "failed_stage": stage,
                "exception": repr(exc),
                "accepted_Day375_state_preserved": True,
                "state_mutation_executed": False,
                "automatic_rerun_authorized": False,
                "pressure_refresh_accepted": False,
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
