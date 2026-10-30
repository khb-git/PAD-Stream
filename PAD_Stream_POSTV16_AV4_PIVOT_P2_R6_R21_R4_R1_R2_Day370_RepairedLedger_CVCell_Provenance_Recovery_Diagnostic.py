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

M = "POSTV16-AV4-PIVOT-P2-R6-R21-R4-R1-R2"
NAME = "Day370 Repaired-Ledger CV-Cell Provenance Recovery Diagnostic"

PASS = "AV4PIVOTP2R6R21R4R1R2_DAY370_REPAIRED_LEDGER_CVCELL_PROVENANCE_RECOVERY_DIAGNOSTIC_PASS_NO_STATE_MUTATION"
BLOCK = "AV4PIVOTP2R6R21R4R1R2_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "c61f2615c79818b34831c49737c7f39aa2771edd"

R4R1R1_RUNNER = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R1_Day370_BaseGrid_CVOwnership_Decomposition_Audit.py"
R4R1R1_BLOB = "731346bebf1668ae1ef695a976d0ffacc4bbef7e"
R19_RUNNER = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R19_Controlled_Remaining_Group_Coupled_Global_Reconciliation_Execution.py"
R19_BLOB = "2626e4a08660a907752be5aca70d29f69dd2a71e"
R3_RUNNER = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R21_R3_FirstIteration_PressureInduced_CapacityLoss_Diagnostic_Freeze.py"
R3_BLOB = "380ffb9f0a8a2f6141e2fd2362d57fe5c9d1ec1c"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

D370 = BASE / (
    "POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_R1_"
    "CompletedComponent_CellMembership_Identity_Repair_and_Controlled_Projection"
)
R19 = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R19_Controlled_Day375_Remaining_NonExecuted_R7_"
    "Group_Coupled_Global_CVConservative_Reconciliation_Execution"
)
R20 = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R20_Day375_Globally_Reconciled_"
    "Provisional_State_Closure_and_Acceptance_Audit"
)
R3DIR = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R21_R3_FirstIteration_"
    "PressureInduced_LocalCapacityLoss_Diagnostic_Freeze"
)
R4R1R1 = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R1_"
    "Day370_BaseGrid_CVOwnership_Decomposition_Audit"
)

D370_STATE = "POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_R1_Repaired_Day370_State.npz"
R19_STATE = "POSTV16_AV4_PIVOT_P2_R6_R19_Provisional_Globally_Reconciled_Day375_State.npz"
R19_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R19_Artifact_Manifest.csv"
R20_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R20_Summary.json"
R20_ACCEPTANCE = "POSTV16_AV4_PIVOT_P2_R6_R20_Day375_State_Acceptance_Contract.json"
R20_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R20_Artifact_Manifest.csv"
R3_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R21_R3_Summary.json"
R3_CELL_AUDIT = "POSTV16_AV4_PIVOT_P2_R6_R21_R3_Violating_Cell_Audit.csv"
R3_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R21_R3_Artifact_Manifest.csv"
R4R1R1_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R1_Summary.json"
R4R1R1_DECISION = "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R1_Decision_Contract.json"
R4R1R1_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R1_Artifact_Manifest.csv"

OUT = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R2_"
    "Day370_RepairedLedger_CVCell_Provenance_Recovery_Diagnostic"
)
BLK = BASE / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R2_BLOCKED"

NCELL = 37500
TOL = 1e-7


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


def selftest() -> None:
    cv = np.asarray([0, 1, 1], dtype=np.int64)
    cell = np.asarray([2, 3, 3], dtype=np.int64)
    mass = np.asarray([1.0, 2.0, -0.5])
    g = np.bincount(cell, weights=mass, minlength=5)
    c = np.bincount(cv, weights=mass, minlength=3)
    assert np.allclose(g, [0, 0, 1, 1.5, 0])
    assert np.allclose(c, [1, 1.5, 0])
    print("POSTV16 AV4 PIVOT P2-R6-R21-R4-R1-R2 structural self-test: PASS")


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
        summary_path = out / "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R2_Summary.json"
        block_path = block / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R2_Blocked_Report.json"
        if summary_path.is_file():
            print("[PASS] formal R6-R21-R4-R1-R2 PASS already exists; immutable outcome preserved.")
            return 0
        gate("no_preexisting_R6R21R4R1R2_BLOCK", not block_path.exists())

        stage = "repository_authority"
        gate("branch_exact", gt(root, "branch", "--show-current") == BRANCH)
        gate("parent_is_R6R21R4R1R1", gt(root, "rev-parse", "HEAD^") == PARENT)
        gate("repository_clean", gt(root, "status", "--porcelain") == "")
        for filename, blob, label in [
            (R4R1R1_RUNNER, R4R1R1_BLOB, "R6R21R4R1R1"),
            (R19_RUNNER, R19_BLOB, "R6R19"),
            (R3_RUNNER, R3_BLOB, "R6R21R3"),
        ]:
            gate(f"{label}_blob_exact", gt(root, "hash-object", str(root / filename)) == blob)

        stage = "R4R1R1_authority"
        r411 = drive / R4R1R1
        manifest(r411, R4R1R1_MANIFEST)
        s411 = js(r411 / R4R1R1_SUMMARY)
        d411 = js(r411 / R4R1R1_DECISION)
        gate(
            "R4R1R1_status_exact",
            s411.get("status") ==
            "AV4PIVOTP2R6R21R4R1R1_DAY370_BASEGRID_CVOWNERSHIP_DECOMPOSITION_AUDIT_PASS_NO_STATE_MUTATION",
        )
        gate("R4R1R2_authorized", d411.get("P2_R6_R21_R4_R1_R2_authorized") is True)
        gate(
            "R4R1R1_standard_provenance_not_reconstructable",
            s411.get("Day370_standard_explicit_CV_cell_provenance_reconstructable") is False,
        )
        gate("R4R1R1_no_state_mutation", s411.get("state_mutation_executed") is False)

        stage = "accepted_state_authority"
        r20 = drive / R20
        manifest(r20, R20_MANIFEST)
        s20 = js(r20 / R20_SUMMARY)
        a20 = js(r20 / R20_ACCEPTANCE)
        accepted_sha = str(a20["accepted_Day375_state_sha256"])
        gate("R20_accepted_state_true", a20.get("accepted_Day375_state") is True)
        gate("accepted_SHA_matches_summary", accepted_sha == s20["accepted_Day375_state_sha256"])

        r19 = drive / R19
        manifest(r19, R19_MANIFEST)
        r19_state = r19 / R19_STATE
        gate("R19_accepted_state_SHA_exact", sha(r19_state) == accepted_sha, sha(r19_state))

        r3dir = drive / R3DIR
        manifest(r3dir, R3_MANIFEST)
        s3 = js(r3dir / R3_SUMMARY)
        rows3 = csvr(r3dir / R3_CELL_AUDIT)
        gate("R3_PASS", s3.get("status") == "AV4PIVOTP2R6R21R3_FIRST_ITERATION_PRESSURE_INDUCED_CAPACITY_LOSS_DIAGNOSTIC_FREEZE_PASS_NO_STATE_MUTATION")
        gate("R3_source_count_9", len(rows3) == 9, len(rows3))

        stage = "Day370_repaired_ledger_load"
        d370_path = drive / D370 / D370_STATE
        gate("Day370_state_present", d370_path.is_file(), str(d370_path))
        d370_sha = sha(d370_path)

        with np.load(d370_path, allow_pickle=False) as z:
            required = [
                "cv_component_mass_kg",
                "grid_component_mass_kg",
                "existing_pair_cv",
                "existing_pair_cell",
                "original_existing_pair_contribution_kg",
                "repaired_existing_pair_contribution_kg",
                "halo_cv",
                "halo_cell",
                "repaired_halo_contribution_kg",
            ]
            missing = [k for k in required if k not in z.files]
            gate("Day370_required_repaired_ledger_fields_present", not missing, missing)

            cv_mass = np.asarray(z["cv_component_mass_kg"], dtype=float).reshape(-1)
            grid_mass = np.asarray(z["grid_component_mass_kg"], dtype=float).reshape(-1)

            pair_cv = np.asarray(z["existing_pair_cv"], dtype=np.int64).reshape(-1)
            pair_cell = np.asarray(z["existing_pair_cell"], dtype=np.int64).reshape(-1)
            original_pair = np.asarray(z["original_existing_pair_contribution_kg"], dtype=float).reshape(-1)
            repaired_pair = np.asarray(z["repaired_existing_pair_contribution_kg"], dtype=float).reshape(-1)

            halo_cv = np.asarray(z["halo_cv"], dtype=np.int64).reshape(-1)
            halo_cell = np.asarray(z["halo_cell"], dtype=np.int64).reshape(-1)
            repaired_halo = np.asarray(z["repaired_halo_contribution_kg"], dtype=float).reshape(-1)

            day = float(np.asarray(z["day"]).reshape(()))
            schema = [{
                "key": key,
                "dtype": str(np.asarray(z[key]).dtype),
                "shape": "x".join(str(x) for x in np.asarray(z[key]).shape),
                "size": int(np.asarray(z[key]).size),
            } for key in z.files]

        gate("Day370_grid_size_exact", grid_mass.size == NCELL, grid_mass.shape)
        gate("Day370_pair_lengths_consistent", len(pair_cv) == len(pair_cell) == len(original_pair) == len(repaired_pair))
        gate("Day370_halo_lengths_consistent", len(halo_cv) == len(halo_cell) == len(repaired_halo))
        gate("Day370_CV_indices_in_range", int(max(pair_cv.max(initial=0), halo_cv.max(initial=0))) < cv_mass.size)

        stage = "Day370_repaired_ledger_reconstruction"
        repaired_pair_grid = np.bincount(pair_cell, weights=repaired_pair, minlength=NCELL)
        repaired_halo_grid = np.bincount(halo_cell, weights=repaired_halo, minlength=NCELL)
        repaired_grid = repaired_pair_grid + repaired_halo_grid

        repaired_pair_cv = np.bincount(pair_cv, weights=repaired_pair, minlength=cv_mass.size)
        repaired_halo_cv = np.bincount(halo_cv, weights=repaired_halo, minlength=cv_mass.size)
        repaired_cv = repaired_pair_cv + repaired_halo_cv

        original_pair_grid = np.bincount(pair_cell, weights=original_pair, minlength=NCELL)
        repair_delta_grid = repaired_pair_grid - original_pair_grid

        max_grid_error = float(np.max(np.abs(repaired_grid - grid_mass)))
        max_cv_error = float(np.max(np.abs(repaired_cv - cv_mass)))
        total_grid_error = float(abs(repaired_grid.sum() - grid_mass.sum()))
        total_cv_error = float(abs(repaired_cv.sum() - cv_mass.sum()))
        grid_vs_cv_total_error = float(abs(grid_mass.sum() - cv_mass.sum()))
        residual_grid = grid_mass - repaired_grid

        exact_grid = max_grid_error <= TOL
        exact_cv = max_cv_error <= TOL
        full_provenance = bool(exact_grid and exact_cv)

        stage = "source_cell_repaired_provenance_audit"
        pos_by_cell: dict[int, float] = {}
        neg_by_cell: dict[int, float] = {}
        cv_count_by_cell: dict[int, set[int]] = {}

        for cv, c, m in zip(pair_cv.tolist(), pair_cell.tolist(), repaired_pair.tolist()):
            cv, c, m = int(cv), int(c), float(m)
            if abs(m) <= 1e-13:
                continue
            cv_count_by_cell.setdefault(c, set()).add(cv)
            if m > 0:
                pos_by_cell[c] = pos_by_cell.get(c, 0.0) + m
            else:
                neg_by_cell[c] = neg_by_cell.get(c, 0.0) + abs(m)

        for cv, c, m in zip(halo_cv.tolist(), halo_cell.tolist(), repaired_halo.tolist()):
            cv, c, m = int(cv), int(c), float(m)
            if abs(m) <= 1e-13:
                continue
            cv_count_by_cell.setdefault(c, set()).add(cv)
            if m > 0:
                pos_by_cell[c] = pos_by_cell.get(c, 0.0) + m
            else:
                neg_by_cell[c] = neg_by_cell.get(c, 0.0) + abs(m)

        source_rows = []
        source_shortfall_count = 0
        source_shortfall_total = 0.0
        for r in rows3:
            c = int(r["flat_cell"])
            excess = float(r["excess_kg"])
            positive = float(pos_by_cell.get(c, 0.0))
            negative = float(neg_by_cell.get(c, 0.0))
            shortfall = max(0.0, excess - positive)
            if shortfall > TOL:
                source_shortfall_count += 1
                source_shortfall_total += shortfall

            source_rows.append({
                "flat_cell": c,
                "k": int(r["k"]),
                "j": int(r["j"]),
                "i": int(r["i"]),
                "pressure_capacity_excess_kg": excess,
                "Day370_grid_mass_kg": float(grid_mass[c]),
                "repaired_ledger_net_mass_kg": float(repaired_grid[c]),
                "repaired_ledger_residual_kg": float(residual_grid[c]),
                "repaired_positive_CV_attributed_mass_kg": positive,
                "repaired_negative_abs_CV_attributed_mass_kg": negative,
                "repaired_unique_CV_count": len(cv_count_by_cell.get(c, set())),
                "positive_CV_availability_minus_excess_kg": positive - excess,
                "positive_CV_availability_shortfall_kg": shortfall,
            })

        if full_provenance:
            gate(
                "full_repaired_ledger_gives_positive_CV_availability_for_all_9_sources",
                source_shortfall_count == 0,
                {"count": source_shortfall_count, "kg": source_shortfall_total},
            )

        stage = "recovery_classification"
        if full_provenance and source_shortfall_count == 0:
            classification = (
                "R6R21R4R1R2_DAY370_REPAIRED_PAIR_HALO_LEDGER_EXACTLY_RECOVERS_"
                "FULL_CVCELL_PROVENANCE_RECONCILIATION_SEMANTICS_FREEZE_NEXT"
            )
            next_name = (
                "Recovered Day370 Full CV-Cell Provenance Pressure-Capacity "
                "Reconciliation Semantics Design Freeze"
            )
        elif exact_cv and not exact_grid:
            classification = (
                "R6R21R4R1R2_DAY370_CV_TOTALS_RECOVERED_BUT_CARTESIAN_RESIDUAL_REMAINS_"
                "RESIDUAL_PROVENANCE_DIAGNOSTIC_NEXT"
            )
            next_name = "Day370 Cartesian Residual Provenance Diagnostic"
        elif exact_grid and not exact_cv:
            classification = (
                "R6R21R4R1R2_DAY370_CARTESIAN_GRID_RECOVERED_BUT_CV_TOTAL_MISMATCH_"
                "CV_IDENTITY_DIAGNOSTIC_NEXT"
            )
            next_name = "Day370 CV Identity / Contribution Reconciliation Diagnostic"
        else:
            classification = (
                "R6R21R4R1R2_DAY370_REPAIRED_LEDGER_DOES_NOT_FULLY_RECOVER_CVCELL_"
                "PROVENANCE_DEEPER_PROVENANCE_DIAGNOSTIC_NEXT"
            )
            next_name = "Day370 Deep CV-Cell Provenance Recovery Diagnostic"

        diagnostic = {
            "accepted_Day375_state_sha256": accepted_sha,
            "Day370_state_sha256": d370_sha,
            "Day370_day": day,
            "repaired_pair_entry_count": int(len(repaired_pair)),
            "repaired_halo_entry_count": int(len(repaired_halo)),
            "Day370_CV_count": int(cv_mass.size),
            "maximum_grid_reconstruction_error_kg": max_grid_error,
            "maximum_CV_reconstruction_error_kg": max_cv_error,
            "total_grid_reconstruction_error_kg": total_grid_error,
            "total_CV_reconstruction_error_kg": total_cv_error,
            "grid_total_vs_CV_total_error_kg": grid_vs_cv_total_error,
            "maximum_unattributed_cartesian_residual_kg": float(np.max(np.abs(residual_grid))),
            "total_absolute_unattributed_cartesian_residual_kg": float(np.sum(np.abs(residual_grid))),
            "repaired_pair_delta_vs_original_L1_kg": float(np.sum(np.abs(repair_delta_grid))),
            "repaired_pair_delta_vs_original_max_cell_kg": float(np.max(np.abs(repair_delta_grid))),
            "repaired_ledger_exactly_reconstructs_Day370_grid": exact_grid,
            "repaired_ledger_exactly_reconstructs_Day370_CV_masses": exact_cv,
            "full_Day370_CV_cell_provenance_recovered": full_provenance,
            "source_cell_count": len(source_rows),
            "source_cells_with_positive_CV_availability_shortfall_after_recovery": source_shortfall_count,
            "source_positive_CV_availability_shortfall_after_recovery_kg": source_shortfall_total,
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
            "P2_R6_R21_R4_R1_R3_authorized": True,
            "P2_R6_R21_R4_R1_R3_name": next_name,
            "P2_R6_R21_R4_R1_R3_design_or_diagnostic_only": True,
            "full_Day370_CV_cell_provenance_recovered": full_provenance,
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
        (out / "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R2_Summary.json").write_bytes(jb(summary))
        (out / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R2_Source_Cell_Recovered_Provenance_Audit.csv").write_bytes(csvb(source_rows))
        (out / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R2_Day370_State_Schema.csv").write_bytes(csvb(schema))
        (out / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R2_Diagnostic_Contract.json").write_bytes(jb(diagnostic))
        (out / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R2_Decision_Contract.json").write_bytes(jb(decision))
        (out / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R2_Final_Gate_Matrix.csv").write_bytes(csvb(gates))

        manifest_rows = []
        for p in sorted(out.iterdir()):
            if p.is_file():
                manifest_rows.append({
                    "file": p.name,
                    "sha256": sha(p),
                    "bytes": p.stat().st_size,
                })
        (out / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R2_Artifact_Manifest.csv").write_bytes(csvb(manifest_rows))

        print("=" * 190)
        print(M, "PASS")
        print("Accepted Day375 state SHA256                 :", accepted_sha)
        print("Day370 state SHA256                          :", d370_sha)
        print("Day370 CV count                              :", cv_mass.size)
        print("Repaired pair / halo entries                 :", len(repaired_pair), "/", len(repaired_halo))
        print("Maximum grid reconstruction error kg         :", max_grid_error)
        print("Maximum CV reconstruction error kg           :", max_cv_error)
        print("Grid total vs CV total error kg              :", grid_vs_cv_total_error)
        print("Max unattributed Cartesian residual kg        :", float(np.max(np.abs(residual_grid))))
        print("Total abs unattributed residual kg            :", float(np.sum(np.abs(residual_grid))))
        print("Full Day370 CV-cell provenance recovered      :", full_provenance)
        print("Source positive-attribution shortfall count   :", source_shortfall_count)
        print("Source positive-attribution shortfall kg      :", source_shortfall_total)
        print("State mutation / pressure acceptance          : False / False")
        print("R4-R1-R3 design/diagnostic authorized         : True")
        print("Darcy/Pollock/TOF / time / P3                 : False / False / False")
        print("=" * 190)
        return 0

    except Exception as exc:
        block.mkdir(parents=True, exist_ok=True)
        p = block / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R2_Blocked_Report.json"
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
