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

M = "POSTV16-AV4-PIVOT-P2-R6-R21-R4-R1-R1"
NAME = "Day370 Base-Grid / CV-Ownership Representation Decomposition Audit"

PASS = "AV4PIVOTP2R6R21R4R1R1_DAY370_BASEGRID_CVOWNERSHIP_DECOMPOSITION_AUDIT_PASS_NO_STATE_MUTATION"
BLOCK = "AV4PIVOTP2R6R21R4R1R1_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "5b41a08421f1be033f46ddffd908cf7509044e05"

R19_RUNNER = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R19_Controlled_Remaining_Group_Coupled_Global_Reconciliation_Execution.py"
R19_BLOB = "2626e4a08660a907752be5aca70d29f69dd2a71e"
R3_RUNNER = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R21_R3_FirstIteration_PressureInduced_CapacityLoss_Diagnostic_Freeze.py"
R3_BLOB = "380ffb9f0a8a2f6141e2fd2362d57fe5c9d1ec1c"
R4_RUNNER = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R21_R4_PressureCapacity_Coupled_Reconciliation_Semantics_Freeze.py"
R4_BLOB = "0e72d29d9da8ab680d7bbb321ec5006f706c6ffa"
R4R1_RUNNER = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_FaceDomain_Hall_Bottleneck_Localization.py"
R4R1_BLOB = "4db3e4a84fdb9267c0428c90cb2283267dc96746"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

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
D370 = BASE / (
    "POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_R1_"
    "CompletedComponent_CellMembership_Identity_Repair_and_Controlled_Projection"
)
R4R1_BLOCK = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_BLOCKED/"
    "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_Blocked_Report.json"
)

R19_STATE = "POSTV16_AV4_PIVOT_P2_R6_R19_Provisional_Globally_Reconciled_Day375_State.npz"
R19_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R19_Artifact_Manifest.csv"
R20_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R20_Summary.json"
R20_ACCEPTANCE = "POSTV16_AV4_PIVOT_P2_R6_R20_Day375_State_Acceptance_Contract.json"
R20_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R20_Artifact_Manifest.csv"
R3_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R21_R3_Summary.json"
R3_CELL_AUDIT = "POSTV16_AV4_PIVOT_P2_R6_R21_R3_Violating_Cell_Audit.csv"
R3_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R21_R3_Artifact_Manifest.csv"
D370_STATE = "POSTV16_AV4_PIVOT_P2_R5_G2A_R4_R1_R1_R1_Repaired_Day370_State.npz"

OUT = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R1_"
    "Day370_BaseGrid_CVOwnership_Decomposition_Audit"
)
BLK = BASE / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R1_BLOCKED"

GRID = (15, 50, 50)
NCELL = 37500
TOL = 1.0e-7

R4R1_STATUS = "AV4PIVOTP2R6R21R4R1_TECHNICAL_OR_AUTHORITY_BLOCK"
R4R1_STAGE = "first_iteration_reproduction"
R4R1_EXCEPTION = "GateError('all_sources_have_positive_contribution_availability')"


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
        for k in row:
            if k not in fields:
                fields.append(k)
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
    x = np.asarray([0, 1, 1], dtype=np.int64)
    w = np.asarray([1.0, 2.0, -0.5])
    b = np.bincount(x, weights=w, minlength=3)
    assert np.allclose(b, [1.0, 1.5, 0.0])
    print("POSTV16 AV4 PIVOT P2-R6-R21-R4-R1-R1 structural self-test: PASS")


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
        summary_path = out / "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R1_Summary.json"
        block_path = block / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R1_Blocked_Report.json"
        if summary_path.is_file():
            print("[PASS] formal R6-R21-R4-R1-R1 PASS already exists; immutable outcome preserved.")
            return 0
        gate("no_preexisting_R6R21R4R1R1_BLOCK", not block_path.exists())

        stage = "repository_authority"
        gate("branch_exact", gt(root, "branch", "--show-current") == BRANCH)
        gate("parent_is_R6R21R4R1", gt(root, "rev-parse", "HEAD^") == PARENT)
        gate("repository_clean", gt(root, "status", "--porcelain") == "")
        for filename, blob, label in [
            (R19_RUNNER, R19_BLOB, "R6R19"),
            (R3_RUNNER, R3_BLOB, "R6R21R3"),
            (R4_RUNNER, R4_BLOB, "R6R21R4"),
            (R4R1_RUNNER, R4R1_BLOB, "R6R21R4R1"),
        ]:
            gate(f"{label}_blob_exact", gt(root, "hash-object", str(root / filename)) == blob)

        stage = "R6R21R4R1_BLOCK_authority"
        r4r1_block = drive / R4R1_BLOCK
        gate("R6R21R4R1_BLOCK_present", r4r1_block.is_file(), str(r4r1_block))
        r4r1_sha = sha(r4r1_block)
        b41 = js(r4r1_block)
        gate("R6R21R4R1_BLOCK_status_exact", b41.get("status") == R4R1_STATUS, b41.get("status"))
        gate("R6R21R4R1_BLOCK_stage_exact", b41.get("failed_stage") == R4R1_STAGE, b41.get("failed_stage"))
        gate("R6R21R4R1_BLOCK_exception_exact", b41.get("exception") == R4R1_EXCEPTION, b41.get("exception"))
        gate("accepted_state_preserved", b41.get("accepted_Day375_state_preserved") is True)
        gate("no_state_mutation", b41.get("state_mutation_executed") is False)

        stage = "accepted_state_and_R3_authority"
        r20 = drive / R20
        manifest(r20, R20_MANIFEST)
        s20 = js(r20 / R20_SUMMARY)
        a20 = js(r20 / R20_ACCEPTANCE)
        accepted_sha = str(a20["accepted_Day375_state_sha256"])
        gate("R6R20_accepted_state_true", a20.get("accepted_Day375_state") is True)
        gate("accepted_SHA_matches_summary", accepted_sha == s20["accepted_Day375_state_sha256"])

        r19 = drive / R19
        manifest(r19, R19_MANIFEST)
        state_path = r19 / R19_STATE
        gate("accepted_state_file_SHA_exact", sha(state_path) == accepted_sha, sha(state_path))

        r3dir = drive / R3DIR
        manifest(r3dir, R3_MANIFEST)
        s3 = js(r3dir / R3_SUMMARY)
        rows3 = csvr(r3dir / R3_CELL_AUDIT)
        gate("R3_PASS_exact", s3.get("status") == "AV4PIVOTP2R6R21R3_FIRST_ITERATION_PRESSURE_INDUCED_CAPACITY_LOSS_DIAGNOSTIC_FREEZE_PASS_NO_STATE_MUTATION")
        gate("R3_source_count_9", len(rows3) == 9, len(rows3))

        with np.load(state_path, allow_pickle=False) as z:
            accepted_mass = np.asarray(z["provisional_grid_component_mass_kg"], dtype=float).reshape(-1)
            pair_cv = np.asarray(z["existing_pair_cv"], dtype=np.int64).reshape(-1)
            pair_cell = np.asarray(z["existing_pair_cell"], dtype=np.int64).reshape(-1)
            pair_mass = np.asarray(z["reconciled_existing_pair_contribution_kg"], dtype=float).reshape(-1)
            halo_cv = np.asarray(z["halo_cv"], dtype=np.int64).reshape(-1)
            halo_cell = np.asarray(z["halo_cell"], dtype=np.int64).reshape(-1)
            halo_mass = np.asarray(z["halo_contribution_kg"], dtype=float).reshape(-1)
            preserved_cv_mass = np.asarray(z["preserved_CV_mass_kg"], dtype=float).reshape(-1)

        stage = "R19_representation_decomposition"
        pair_grid = np.bincount(pair_cell, weights=pair_mass, minlength=NCELL)
        halo_grid = np.bincount(halo_cell, weights=halo_mass, minlength=NCELL)
        transport_grid = pair_grid + halo_grid
        old_grid_reconstructed = accepted_mass - transport_grid

        cv_from_ledger = (
            np.bincount(pair_cv, weights=pair_mass, minlength=len(preserved_cv_mass))
            + np.bincount(halo_cv, weights=halo_mass, minlength=len(preserved_cv_mass))
        )
        max_cv_ledger_error = float(np.max(np.abs(cv_from_ledger - preserved_cv_mass)))
        gate("R19_preserved_CV_mass_is_pair_plus_halo_only", max_cv_ledger_error <= TOL, max_cv_ledger_error)

        d370_path = drive / D370 / D370_STATE
        gate("Day370_state_present", d370_path.is_file(), str(d370_path))
        d370_sha = sha(d370_path)

        with np.load(d370_path, allow_pickle=False) as z:
            d370_keys = list(z.files)
            gate("Day370_grid_component_mass_present", "grid_component_mass_kg" in z.files, d370_keys)
            old_grid_d370 = np.asarray(z["grid_component_mass_kg"], dtype=float).reshape(-1)

            schema_rows = []
            for key in z.files:
                arr = np.asarray(z[key])
                schema_rows.append({
                    "key": key,
                    "dtype": str(arr.dtype),
                    "shape": "x".join(str(x) for x in arr.shape),
                    "size": int(arr.size),
                    "ownership_relevant_name": any(tok in key.lower() for tok in (
                        "cv", "cell", "mass", "contribution", "halo", "pair", "grid"
                    )),
                })

            # Conservative test for standard explicit ledgers if present.
            candidate_grid = np.zeros(NCELL, dtype=float)
            candidate_components = []
            explicit_ledger_available = False

            if all(k in z.files for k in (
                "existing_pair_cell",
                "reconciled_existing_pair_contribution_kg",
            )):
                pc = np.asarray(z["existing_pair_cell"], dtype=np.int64).reshape(-1)
                pm = np.asarray(z["reconciled_existing_pair_contribution_kg"], dtype=float).reshape(-1)
                candidate_grid += np.bincount(pc, weights=pm, minlength=NCELL)
                candidate_components.append("existing_pair")
                explicit_ledger_available = True

            if all(k in z.files for k in ("halo_cell", "halo_contribution_kg")):
                hc = np.asarray(z["halo_cell"], dtype=np.int64).reshape(-1)
                hm = np.asarray(z["halo_contribution_kg"], dtype=float).reshape(-1)
                candidate_grid += np.bincount(hc, weights=hm, minlength=NCELL)
                candidate_components.append("halo")
                explicit_ledger_available = True

        old_grid_identity_error = float(np.max(np.abs(old_grid_reconstructed - old_grid_d370)))
        gate("R19_old_grid_reconstructs_exact_Day370_grid", old_grid_identity_error <= TOL, old_grid_identity_error)

        candidate_full_reconstruction_error = None
        candidate_full_reconstructable = False
        if explicit_ledger_available:
            candidate_full_reconstruction_error = float(np.max(np.abs(candidate_grid - old_grid_d370)))
            candidate_full_reconstructable = candidate_full_reconstruction_error <= TOL

        stage = "source_cell_ownership_audit"
        positive_by_cell: dict[int, float] = {}
        negative_abs_by_cell: dict[int, float] = {}
        net_by_cell: dict[int, float] = {}

        for c, m in zip(pair_cell.tolist(), pair_mass.tolist()):
            c = int(c); m = float(m)
            net_by_cell[c] = net_by_cell.get(c, 0.0) + m
            if m > 0.0:
                positive_by_cell[c] = positive_by_cell.get(c, 0.0) + m
            elif m < 0.0:
                negative_abs_by_cell[c] = negative_abs_by_cell.get(c, 0.0) + abs(m)

        for c, m in zip(halo_cell.tolist(), halo_mass.tolist()):
            c = int(c); m = float(m)
            net_by_cell[c] = net_by_cell.get(c, 0.0) + m
            if m > 0.0:
                positive_by_cell[c] = positive_by_cell.get(c, 0.0) + m
            elif m < 0.0:
                negative_abs_by_cell[c] = negative_abs_by_cell.get(c, 0.0) + abs(m)

        source_rows = []
        availability_shortfall_count = 0
        total_availability_shortfall = 0.0
        total_old_grid_in_sources = 0.0
        all_shortfalls_explained_by_old_grid = True

        for r in rows3:
            c = int(r["flat_cell"])
            excess = float(r["excess_kg"])
            accepted = float(accepted_mass[c])
            base = float(old_grid_d370[c])
            pos = float(positive_by_cell.get(c, 0.0))
            neg = float(negative_abs_by_cell.get(c, 0.0))
            net = float(net_by_cell.get(c, 0.0))
            shortfall = max(0.0, excess - pos)
            if shortfall > TOL:
                availability_shortfall_count += 1
                total_availability_shortfall += shortfall
                if base + TOL < shortfall:
                    all_shortfalls_explained_by_old_grid = False

            total_old_grid_in_sources += base

            source_rows.append({
                "flat_cell": c,
                "k": int(r["k"]),
                "j": int(r["j"]),
                "i": int(r["i"]),
                "pressure_capacity_excess_kg": excess,
                "accepted_cell_mass_kg": accepted,
                "Day370_old_grid_mass_kg": base,
                "R19_pair_halo_net_mass_kg": net,
                "R19_pair_halo_positive_mass_kg": pos,
                "R19_pair_halo_negative_abs_mass_kg": neg,
                "positive_CV_attributed_availability_minus_excess_kg": pos - excess,
                "positive_CV_attributed_shortfall_kg": shortfall,
                "old_grid_covers_attribution_shortfall": bool(base + TOL >= shortfall),
                "old_grid_fraction_of_accepted_mass": (
                    base / accepted if abs(accepted) > 1e-30 else None
                ),
            })

        gate(
            "R4R1_failure_reproduced_as_positive_CV_attribution_shortfall",
            availability_shortfall_count > 0,
            availability_shortfall_count,
        )
        gate(
            "all_positive_CV_attribution_shortfalls_are_explained_by_old_grid_mass",
            all_shortfalls_explained_by_old_grid,
            total_availability_shortfall,
        )

        stage = "representation_classification"
        if candidate_full_reconstructable:
            classification = (
                "R6R21R4R1R1_DAY370_BASEGRID_DECOMPOSED_STANDARD_EXPLICIT_CV_CELL_"
                "PROVENANCE_RECONSTRUCTABLE_SEMANTICS_FREEZE_NEXT"
            )
            next_name = "Day370 Full CV-Cell Provenance Reconstruction Semantics Freeze"
        else:
            classification = (
                "R6R21R4R1R1_DAY370_BASEGRID_DECOMPOSED_CV_PROVENANCE_NOT_EXPLICITLY_"
                "RECONSTRUCTABLE_FROM_STANDARD_STATE_LEDGERS_RECOVERY_DIAGNOSTIC_NEXT"
            )
            next_name = "Day370 Base Cartesian Mass CV-Provenance Recovery Diagnostic"

        diagnostic = {
            "R6R21R4R1_BLOCK_sha256": r4r1_sha,
            "accepted_Day375_state_sha256": accepted_sha,
            "Day370_state_sha256": d370_sha,
            "R19_representation_identity": (
                "accepted_grid = Day370_old_grid + R19_existing_pair_contributions + R19_halo_H2_contributions"
            ),
            "R19_preserved_CV_mass_semantics": "pair_plus_halo_H2_transport_contributions_only",
            "maximum_R19_preserved_CV_ledger_error_kg": max_cv_ledger_error,
            "maximum_old_grid_identity_error_kg": old_grid_identity_error,
            "source_cell_count": len(source_rows),
            "source_cells_with_positive_CV_attribution_shortfall": availability_shortfall_count,
            "total_positive_CV_attribution_shortfall_kg": total_availability_shortfall,
            "total_Day370_old_grid_mass_in_source_cells_kg": total_old_grid_in_sources,
            "all_attribution_shortfalls_explained_by_old_grid_mass": all_shortfalls_explained_by_old_grid,
            "Day370_state_keys": d370_keys,
            "Day370_standard_explicit_ledger_components_found": candidate_components,
            "Day370_standard_explicit_ledger_available": explicit_ledger_available,
            "Day370_standard_explicit_ledger_reconstruction_error_kg": candidate_full_reconstruction_error,
            "Day370_standard_explicit_CV_cell_provenance_reconstructable": candidate_full_reconstructable,
            "accepted_transport_state_invalidated": False,
            "state_mutation_executed": False,
        }

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": classification,
            **diagnostic,
            "pressure_refresh_accepted": False,
            "pressure_reconciliation_execution_authorized": False,
            "Darcy_Pollock_TOF_regeneration_executed": False,
            "time_advance_executed": False,
            "P3_authorized": False,
        }

        decision = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "P2_R6_R21_R4_R1_R2_authorized": True,
            "P2_R6_R21_R4_R1_R2_name": next_name,
            "P2_R6_R21_R4_R1_R2_design_or_diagnostic_only": True,
            "Day370_standard_explicit_CV_cell_provenance_reconstructable": candidate_full_reconstructable,
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
        (out / "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R1_Summary.json").write_bytes(jb(summary))
        (out / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R1_Source_Cell_Ownership_Audit.csv").write_bytes(csvb(source_rows))
        (out / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R1_Day370_State_Schema.csv").write_bytes(csvb(schema_rows))
        (out / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R1_Diagnostic_Contract.json").write_bytes(jb(diagnostic))
        (out / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R1_Decision_Contract.json").write_bytes(jb(decision))
        (out / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R1_Final_Gate_Matrix.csv").write_bytes(csvb(gates))

        manifest_rows = []
        for p in sorted(out.iterdir()):
            if p.is_file():
                manifest_rows.append({"file": p.name, "sha256": sha(p), "bytes": p.stat().st_size})
        (out / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R1_Artifact_Manifest.csv").write_bytes(csvb(manifest_rows))

        print("=" * 190)
        print(M, "PASS")
        print("R4-R1 BLOCK SHA256                         :", r4r1_sha)
        print("Accepted Day375 state SHA256               :", accepted_sha)
        print("Day370 state SHA256                        :", d370_sha)
        print("Old-grid identity max error kg             :", old_grid_identity_error)
        print("R19 preserved-CV ledger max error kg       :", max_cv_ledger_error)
        print("Source cells                               :", len(source_rows))
        print("Sources with CV-attribution shortfall      :", availability_shortfall_count)
        print("Total CV-attribution shortfall kg          :", total_availability_shortfall)
        print("Total Day370 old-grid mass in sources kg   :", total_old_grid_in_sources)
        print("All shortfalls explained by old-grid mass  :", all_shortfalls_explained_by_old_grid)
        print("Day370 standard explicit ledgers found     :", candidate_components)
        print("Day370 explicit CV-cell provenance exact   :", candidate_full_reconstructable)
        print("State mutation / pressure acceptance       : False / False")
        print("R4-R1-R2 design/diagnostic authorized      : True")
        print("Darcy/Pollock/TOF / time / P3              : False / False / False")
        print("=" * 190)
        return 0

    except Exception as exc:
        block.mkdir(parents=True, exist_ok=True)
        p = block / "POSTV16_AV4_PIVOT_P2_R6_R21_R4_R1_R1_Blocked_Report.json"
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
