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


MILESTONE = "POSTV16-AV4-F4-R3-R3-R3-R2"
PROTOCOL_ID = (
    "POSTV16_AV4_F4_R3_R3_R3_R2_SINGLE_RING_PER_CV_"
    "HORIZONTAL_FACE_OCCUPANCY_EXTENSION_V1"
)

STATUS_PASS = (
    "AV4F4R3R3R3R2_R3R3R3R1_EXACT_S0_LOCAL_SUPPORT_CAPACITY_HALL_DEFICIT_"
    "BOUND_SINGLE_NONRECURSIVE_PER_CV_SAME_LAYER_XY_FACE_NEIGHBOR_OCCUPANCY_"
    "EXTENSION_PROSPECTIVELY_FROZEN_NO_EXECUTION"
)
STATUS_BLOCKED = "AV4F4R3R3R3R2_OCCUPANCY_EXTENSION_FREEZE_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT_R3R3R3R1_COMMIT = "d6099f7b8f0d7afcb7efe248f717298bf87ba8fc"

GRID = [15, 50, 50]
NZ, NY, NX = GRID
BACKGROUND = 0.20
INJECTED = 0.80
MAX_SG = 0.60
EVENT_DAY = 413.78677770818403

EXPECTED_GLOBAL_S0_SURPLUS_KG = 13404390.688116565
EXPECTED_MIN_UNSERVED_KG = 6574010.724504838
EXPECTED_HALL_DEFICIT_KG = 6574010.724213455
EXPECTED_HALL_CV_COUNT = 73714
EXPECTED_HALL_CELL_COUNT = 4119
EXPECTED_HALL_STREAMLINE_COUNT = 1046
EXPECTED_HALL_DEMAND_KG = 20588612.920537915
EXPECTED_HALL_CAPACITY_KG = 14014602.19632446

CLASSIFICATION = "S0_LOCAL_SUPPORT_CAPACITY_HALL_DEFICIT"

# --------------------------------------------------------------------------------------------------
# Exact source authorities.
# --------------------------------------------------------------------------------------------------

R1 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R1_"
    "S0_CV_Cell_Capacity_Hall_Deficit_Localization.py"
)
R1_BLOB = "304f68abf78a55cf00917667cff33e20b415db46"

R3R3 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_"
    "Ownership_Reconciled_Event_MapBack_and_Flow_Refresh_Execution.py"
)
R3R3_BLOB = "b2c129bd067ef75163c3f06de5c15adc53ae5633"

R3R2 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R2_"
    "Bounded_Parent_Ownership_Event_MapBack_Reconciliation_Freeze.py"
)
R3R2_BLOB = "247e1e5b6d3fc83bd81d3dd84f0bbeb88c5280c0"

F2R3 = (
    "PAD_Stream_POSTV16_AV4_F2_R3_"
    "Bounded_Physical_Occupancy_Projection_Execution.py"
)
F2R3_BLOB = "359f3c0edf87e10bb4006cacdd271cd426fed22b"

R2 = (
    "PAD_Stream_V16E35_R2_Source_Conservative_Transport_"
    "Capillary_Split_First_Controlled_Transition.py"
)
R2_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"

# Historical physical precedent only: not an execution dependency.
AV1_R7R7D = (
    "PAD_Stream_POSTV16_AV1_D_R7_R7D_"
    "Horizontal_Face_Halo_Occupancy_Domain_Freeze.py"
)
AV1_R7R7D_BLOB = "bd2873f7fb6b98d4e857c98864b78e2da6f202a4"

SOURCE_BLOBS = {
    R1: R1_BLOB,
    R3R3: R3R3_BLOB,
    R3R2: R3R2_BLOB,
    F2R3: F2R3_BLOB,
    R2: R2_BLOB,
    AV1_R7R7D: AV1_R7R7D_BLOB,
}

# --------------------------------------------------------------------------------------------------
# Formal R1 authority.
# --------------------------------------------------------------------------------------------------

BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

R1_REL = (
    BASE_AV4
    / "POSTV16_AV4_F4_R3_R3_R3_R1_S0_CV_Cell_Capacity_Hall_Deficit_Localization"
)
R1_SUMMARY = "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R1_Summary.json"
R1_DIAG = "POSTV16_AV4_F4_R3_R3_R3_R1_S0_Feasibility_Diagnosis.json"
R1_HANDOFF = "POSTV16_AV4_F4_R3_R3_R3_R1_R3R3R3R2_Handoff_Contract.json"
R1_DECISION = "POSTV16_AV4_F4_R3_R3_R3_R1_Decision_Contract.json"
R1_MANIFEST = "POSTV16_AV4_F4_R3_R3_R3_R1_Artifact_Manifest.csv"

R1_STATUS = (
    "AV4F4R3R3R3R1_R3R3R3_STAGE1_S0_ASSIGNMENT_SCIENTIFIC_FAIL_PRESERVED_"
    "EXACT_CONTINUOUS_MINIMUM_UNSERVED_MASS_AND_RESIDUAL_MINCUT_HALL_WITNESS_"
    "LOCALIZED_NO_REPAIR_SELECTED"
)

OUT_REL = (
    BASE_AV4
    / "POSTV16_AV4_F4_R3_R3_R3_R2_Per_CV_Horizontal_Face_Occupancy_Extension_Freeze"
)
BLOCK_REL = BASE_AV4 / "POSTV16_AV4_F4_R3_R3_R3_R2_BLOCKED"


class GateError(RuntimeError):
    pass


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
    rows = read_csv(directory / name)
    manifest = {r["file"]: r["sha256"] for r in rows}
    if not manifest:
        raise GateError("manifest_empty:" + name)
    for fn, expected in manifest.items():
        p = directory / fn
        if not p.is_file():
            raise GateError("manifest_missing:" + fn)
        if sha256_file(p) != expected:
            raise GateError("manifest_SHA_mismatch:" + fn)
    return manifest


def json_bytes(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


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
    return s.getvalue().encode()


def immutable_publish(out: Path, files: dict[str, bytes]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        p = out / name
        if p.exists() and p.read_bytes() != data:
            raise GateError("existing_output_differs:" + name)
        if not p.exists():
            p.write_bytes(data)


def near(a: Any, b: Any, rtol: float = 1.0e-12, atol: float = 1.0e-6) -> bool:
    aa = float(a)
    bb = float(b)
    return abs(aa - bb) <= max(atol, rtol * max(abs(bb), 1.0))


def self_test() -> None:
    # Per-CV, single-ring, same-layer face-neighbor geometry.
    # Start from one CV with one S0 cell at (k,j,i)=(1,1,1).
    s0 = {(1, 1, 1)}
    h1 = set()
    for k, j, i in s0:
        for dj, di in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            jj = j + dj
            ii = i + di
            if 0 <= jj < 3 and 0 <= ii < 3:
                q = (k, jj, ii)
                if q not in s0:
                    h1.add(q)
    expected = {(1, 1, 0), (1, 1, 2), (1, 0, 1), (1, 2, 1)}
    assert h1 == expected
    assert all(k == 1 for k, _, _ in h1)

    # Non-recursive: newly added H1 cells are not used to create H2.
    assert (1, 1, 3) not in h1

    print(
        "POSTV16-AV4-F4-R3-R3-R3-R2 per-CV horizontal face "
        "occupancy-extension design self-test: PASS"
    )


def main(project_root: Path, drive_root: Path) -> int:
    root = Path(project_root).resolve()
    drive = Path(drive_root).resolve()
    out = drive / OUT_REL
    blocked = drive / BLOCK_REL
    gates: dict[str, dict[str, Any]] = {}
    stage = "preflight"

    def gate(name: str, passed: Any, value: Any = None) -> None:
        ok = bool(passed)
        gates[name] = {"passed": ok, "value": value}
        print(
            f"[{'PASS' if ok else 'FAIL'}] {name}"
            + (f" — {value}" if value is not None else "")
        )
        if not ok:
            raise GateError(name)

    print("=" * 214)
    print(
        "POSTV16-AV4-F4-R3-R3-R3-R2 — PER-CV SINGLE-RING HORIZONTAL "
        "FACE-NEIGHBOR OCCUPANCY-EXTENSION DESIGN FREEZE"
    )
    print("=" * 214)
    print("DESIGN / FREEZE ONLY. NO LP EXECUTION. NO MAPBACK EXECUTION.")
    print("FORMAL R3-R3-R3 SCIENTIFIC FAIL REMAINS IMMUTABLE.")
    print("ONE CANDIDATE ONLY: NON-RECURSIVE SAME-LAYER ±X/±Y FACE NEIGHBORS PER CV.")
    print("NO VERTICAL HALO. NO DIAGONAL HALO. NO SECOND RING. NO CAPACITY RELAXATION.")
    print("NO MASS RELAXATION. NO FLOW REFRESH. NO PHYSICAL-TIME ADVANCE. NO F5.")
    print()

    try:
        stage = "repository_authority"
        parent = git_text(root, "rev-parse", "HEAD^")
        status = git_text(root, "status", "--porcelain")
        gate(
            "repository_parent_is_R3R3R3R1_commit",
            parent == PARENT_R3R3R3R1_COMMIT,
            parent,
        )
        gate("repository_clean", status == "", repr(status))

        for fn, expected in SOURCE_BLOBS.items():
            p = root / fn
            actual = git_blob(p, root) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact", actual == expected, actual)

        stage = "R3R3R3R1_binding"
        d = drive / R1_REL
        gate("R1_output_present", d.is_dir(), str(d))
        manifest = verify_manifest(d, R1_MANIFEST)
        gate("R1_manifest_exact_8", len(manifest) == 8, len(manifest))

        summary = load_json(d / R1_SUMMARY)
        diag = load_json(d / R1_DIAG)
        handoff = load_json(d / R1_HANDOFF)
        decision_in = load_json(d / R1_DECISION)

        gate("R1_status_exact", summary["status"] == R1_STATUS, summary["status"])
        gate("R1_classification_exact", summary["classification"] == CLASSIFICATION, summary["classification"])
        gate(
            "R1_global_S0_surplus_exact",
            near(summary["global_S0_capacity_surplus_kg"], EXPECTED_GLOBAL_S0_SURPLUS_KG),
            summary["global_S0_capacity_surplus_kg"],
        )
        gate(
            "R1_minimum_unserved_exact",
            near(summary["minimum_unserved_mass_kg"], EXPECTED_MIN_UNSERVED_KG),
            summary["minimum_unserved_mass_kg"],
        )
        gate(
            "R1_Hall_counts_exact",
            int(summary["Hall_witness_CV_count"]) == EXPECTED_HALL_CV_COUNT
            and int(summary["Hall_witness_cell_count"]) == EXPECTED_HALL_CELL_COUNT
            and int(summary["Hall_witness_streamline_count"]) == EXPECTED_HALL_STREAMLINE_COUNT,
            {
                "CV": summary["Hall_witness_CV_count"],
                "cell": summary["Hall_witness_cell_count"],
                "streamline": summary["Hall_witness_streamline_count"],
            },
        )
        gate(
            "R1_Hall_deficit_exact",
            near(summary["Hall_deficit_kg"], EXPECTED_HALL_DEFICIT_KG),
            summary["Hall_deficit_kg"],
        )

        witness = diag["residual_mincut_Hall_witness"]
        gate(
            "R1_Hall_demand_capacity_exact",
            near(witness["demand_U_kg"], EXPECTED_HALL_DEMAND_KG)
            and near(witness["capacity_N_of_U_kg"], EXPECTED_HALL_CAPACITY_KG),
            {
                "demand_kg": witness["demand_U_kg"],
                "capacity_kg": witness["capacity_N_of_U_kg"],
            },
        )
        gate(
            "R1_global_capacity_sufficient_but_local_support_infeasible",
            float(summary["global_S0_capacity_surplus_kg"]) > 0.0
            and float(summary["minimum_unserved_mass_kg"]) > 0.0
            and float(summary["Hall_deficit_kg"]) > 0.0,
        )
        gate(
            "R1_repair_not_selected_or_executed",
            decision_in["repair_selected"] is False
            and decision_in["mapback_repair_executed"] is False
            and decision_in["support_domain_changed"] is False
            and decision_in["R3R3R3R2_design_freeze_authorized"] is True
            and decision_in["R3R3R3R2_repair_execution_authorized"] is False,
        )
        gate(
            "R1_handoff_design_only",
            handoff["milestone"] == MILESTONE
            and handoff["authorized"] is True
            and handoff["execution"] is False
            and handoff["support_expansion_authorized"] is False,
        )

        stage = "freeze_single_candidate"

        protocol = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "protocol_id": PROTOCOL_ID,
            "candidate_count": 1,
            "diagnostic_basis": {
                "classification": CLASSIFICATION,
                "global_S0_capacity_surplus_kg": EXPECTED_GLOBAL_S0_SURPLUS_KG,
                "minimum_unserved_mass_kg": EXPECTED_MIN_UNSERVED_KG,
                "Hall_deficit_kg": EXPECTED_HALL_DEFICIT_KG,
                "Hall_witness_CV_count": EXPECTED_HALL_CV_COUNT,
                "Hall_witness_cell_count": EXPECTED_HALL_CELL_COUNT,
                "Hall_witness_streamline_count": EXPECTED_HALL_STREAMLINE_COUNT,
                "implication": (
                    "Capacity exists outside at least one CV subset's current reachable "
                    "S0 neighbor set; the repair must enlarge reachability rather than "
                    "relax mass or physical cell capacity."
                ),
            },
            "historical_precedent": {
                "milestone": "POSTV16-AV1-D-R7-R7D",
                "source_blob": AV1_R7R7D_BLOB,
                "borrowed_geometry_principle":
                    "single non-recursive same-layer x/y Cartesian face-neighbor ring",
                "borrowed_terminal_role":
                    "extension cells are occupancy sinks only, never transport/transit cells",
                "AV4_protocol_is_independent": True,
            },
            "base_incidence": {
                "E0":
                    "exact R3-R3-R2/R3-R3-R3 CV-to-Cartesian pair incidence from frozen SG7D/E37A support",
                "event_CV_mass": "unchanged accepted Day413.78677770818403 CV mass",
                "residual_grid_sidecar":
                    "unchanged frozen F2-R3 residual_grid_component_mass_kg",
                "cell_capacity":
                    "unchanged source-authentic R2/A2-E S=0.80 EOS Cartesian capacity under pre-refresh pressure",
            },
            "per_CV_extension": {
                "definition": (
                    "For each CV j independently, E1_j = E0_j union all in-bounds "
                    "same-layer Cartesian face neighbors (k,j±1,i) and (k,j,i±1) "
                    "of every cell in E0_j."
                ),
                "single_ring": True,
                "nonrecursive": True,
                "vertical_neighbors": False,
                "diagonal_neighbors": False,
                "second_ring": False,
                "new_pair_can_target_globally_S0_cell_not_previously_in_that_CV": True,
                "new_pair_can_target_globally_new_H1_cell": True,
                "extension_cell_role": "terminal occupancy sink only",
                "extension_cell_becomes_streamline_or_transport_CV": False,
                "extension_pair_used_to_generate_more_neighbors": False,
            },
            "hard_constraints_at_execution": {
                "per_CV_mass_exact":
                    "sum_{c in E1_j} x_jc = M_event_j for every CV j",
                "nonnegative_pair_mass": "x_jc >= 0",
                "cell_capacity":
                    "R_c + sum_j x_jc <= C_c for every Cartesian cell c",
                "residual_sidecar_exactly_unchanged": True,
                "no_mass_outside_E1": True,
                "global_component_mass_exact": True,
                "saturation_bound_preserved": "0.20 <= S <= 0.80",
            },
            "lexicographic_objectives_at_execution": {
                "stage_0": "feasibility over frozen E1 only",
                "stage_1":
                    "minimize total mass assigned to newly added E1\\E0 pairs",
                "stage_2":
                    "freeze stage-1 optimum and minimize L1 deviation on original E0 pairs from F2-R3 parent-continuity target",
                "stage_3":
                    "freeze stages 1-2 and minimize L1 deviation on original E0 pairs from raw event EOS target",
                "stage_4":
                    "freeze stages 1-3 and apply deterministic lexicographic pair-rank tie break",
                "physical_meaning": (
                    "Use the minimum amount of occupancy-domain extension necessary; "
                    "then preserve the old parent ownership and event EOS geometry as closely as possible."
                ),
            },
            "mandatory_execution_diagnostics": {
                "E0_pair_count": True,
                "E1_pair_count": True,
                "globally_new_H1_cell_count": True,
                "per_CV_added_pair_count_distribution": True,
                "E1_global_available_capacity_kg": True,
                "minimum_halo_mass_kg": True,
                "halo_mass_fraction_of_event_mapped_mass": True,
                "CVs_using_extension_count": True,
                "streamlines_using_extension_count": True,
                "cells_receiving_extension_mass_count": True,
                "all_CV_equalities": True,
                "all_cell_capacity_inequalities": True,
                "outside_E1_mass_exact_zero": True,
            },
            "failure_semantics": {
                "if_E1_infeasible":
                    "SCIENTIFIC FAIL; preserve exact minimum-unserved/Hall diagnostic for E1",
                "automatic_H2_second_ring": False,
                "automatic_vertical_extension": False,
                "automatic_diagonal_extension": False,
                "capacity_relaxation": False,
                "per_CV_mass_relaxation": False,
                "mass_clipping_or_discard": False,
                "global_rescaling": False,
                "automatic_alternate_repair": False,
            },
            "if_assignment_passes": {
                "same_time_flow_refresh_allowed_in_same_execution": True,
                "exactly_one_event_refresh_total": True,
                "bounded_refreshed_geometry_reprojection_required": True,
                "physical_time_advance_before_reprojection": False,
                "Day500_continuation_in_same_execution": False,
            },
            "prohibitions": {
                "change_accepted_event_CV_state": True,
                "change_raw_F4_internal_operator": True,
                "change_F4_R2_terminal_pass_through": True,
                "change_timestep_floor": True,
                "relax_Smax": True,
                "change_residual_sidecar_during_event_mapback": True,
                "train_or_infer_checkpoint": True,
                "locked_OOD": True,
                "A3_E2": True,
                "CMG": True,
            },
        }

        handoff_out = {
            "milestone": "POSTV16-AV4-F4-R3-R3-R3-R3",
            "name":
                "Controlled Per-CV Single-Ring Horizontal Face Occupancy Extension Execution",
            "authorized": True,
            "execution": True,
            "required_R3R3R3R2_status": STATUS_PASS,
            "candidate_count": 1,
            "candidate": PROTOCOL_ID,
            "scope": [
                "construct exact E1 from E0 using one same-layer ±x/±y face-neighbor ring per CV",
                "solve frozen lexicographic constrained assignment",
                "if infeasible publish scientific FAIL with E1 Hall/min-unserved diagnosis",
                "if feasible certify exact per-CV mass and Cartesian capacity",
                "execute one same-time event flow refresh",
                "execute bounded refreshed-geometry reprojection",
                "publish refreshed event recurrent state and stop",
            ],
            "not_authorized": [
                "H2 or recursive growth",
                "vertical or diagonal halo",
                "capacity or CV-mass relaxation",
                "Day500 physical-time continuation",
                "second event refresh",
                "F5",
                "training",
                "checkpoint inference",
                "A3-E2",
                "CMG",
            ],
        }

        decision = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "R3R3_scientific_FAIL_preserved": True,
            "R3R3R3R1_localization_bound": True,
            "cause_class": CLASSIFICATION,
            "candidate_count": 1,
            "selected_candidate":
                "single_nonrecursive_per_CV_same_layer_xy_face_neighbor_occupancy_extension",
            "candidate_execution_performed": False,
            "LP_execution_performed": False,
            "support_domain_changed_in_freeze": False,
            "capacity_relaxed": False,
            "per_CV_mass_relaxed": False,
            "flow_refresh_executed": False,
            "physical_time_advanced": False,
            "R3R3R3R3_execution_authorized": True,
            "R3R3R4_authorized": False,
            "F5_dataset_generation_authorized": False,
            "training_authorized": False,
            "A3_E2_authorized": False,
            "AV4_general_dynamic_transport_authorized": False,
        }

        summary_out = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "protocol_id": PROTOCOL_ID,
            "cause_class": CLASSIFICATION,
            "global_S0_capacity_surplus_kg": EXPECTED_GLOBAL_S0_SURPLUS_KG,
            "S0_minimum_unserved_mass_kg": EXPECTED_MIN_UNSERVED_KG,
            "S0_Hall_deficit_kg": EXPECTED_HALL_DEFICIT_KG,
            "candidate_count": 1,
            "candidate_execution_performed": False,
            "single_ring": True,
            "same_layer_xy_face_neighbors_only": True,
            "nonrecursive": True,
            "vertical_halo": False,
            "diagonal_halo": False,
            "R3R3R3R3_authorized": True,
            "R3R3R4_authorized": False,
            "F5_authorized": False,
        }

        files = {
            "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R2_Summary.json":
                json_bytes(summary_out),
            "POSTV16_AV4_F4_R3_R3_R3_R2_Frozen_Occupancy_Extension_Protocol.json":
                json_bytes(protocol),
            "POSTV16_AV4_F4_R3_R3_R3_R2_R3R3R3R3_Execution_Handoff_Contract.json":
                json_bytes(handoff_out),
            "POSTV16_AV4_F4_R3_R3_R3_R2_Decision_Contract.json":
                json_bytes(decision),
            "POSTV16_AV4_F4_R3_R3_R3_R2_Final_Gate_Matrix.csv":
                csv_bytes([{"gate": k, **v} for k, v in gates.items()]),
        }
        immutable_publish(out, files)

        manifest_rows = []
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name != "POSTV16_AV4_F4_R3_R3_R3_R2_Artifact_Manifest.csv":
                manifest_rows.append(
                    {
                        "file": p.name,
                        "sha256": sha256_file(p),
                        "bytes": p.stat().st_size,
                    }
                )
        immutable_publish(
            out,
            {
                "POSTV16_AV4_F4_R3_R3_R3_R2_Artifact_Manifest.csv":
                    csv_bytes(manifest_rows)
            },
        )

        print()
        print("=" * 214)
        print(
            "POSTV16-AV4-F4-R3-R3-R3-R2: PER-CV SINGLE-RING HORIZONTAL "
            "FACE OCCUPANCY-EXTENSION DESIGN FREEZE PASS"
        )
        print("=" * 214)
        print("R3-R3-R3 scientific FAIL                : PRESERVED")
        print("S0 global capacity surplus kg            :", EXPECTED_GLOBAL_S0_SURPLUS_KG)
        print("S0 minimum unassignable mass kg          :", EXPECTED_MIN_UNSERVED_KG)
        print("S0 Hall deficit kg                       :", EXPECTED_HALL_DEFICIT_KG)
        print("Frozen candidate count                   : 1")
        print("Extension                                : per-CV same-layer ±x/±y face ring")
        print("Vertical / diagonal / second ring        : False / False / False")
        print("Extension role                           : terminal occupancy only")
        print("Execution / LP in R2                     : False / False")
        print("POSTV16-AV4-F4-R3-R3-R3-R3              : AUTHORIZED")
        print("R3-R3-R4 / F5 / training                 : NOT AUTHORIZED")
        print("=" * 214)
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": MILESTONE,
            "status": STATUS_BLOCKED,
            "failed_stage": stage,
            "exception": repr(exc),
            "gates": gates,
            "R3R3_scientific_FAIL_preserved": True,
            "candidate_execution_performed": False,
            "LP_execution_performed": False,
            "support_domain_changed": False,
            "flow_refresh_executed": False,
            "physical_time_advanced": False,
            "automatic_rerun_authorized": False,
            "R3R3R3R3_execution_authorized": False,
            "R3R3R4_authorized": False,
            "F5_dataset_generation_authorized": False,
            "training_authorized": False,
        }
        data = json_bytes(report)
        p = blocked / "POSTV16_AV4_F4_R3_R3_R3_R2_Blocked_Report.json"
        if p.exists() and p.read_bytes() != data:
            p = blocked / (
                "POSTV16_AV4_F4_R3_R3_R3_R2_Blocked_Report_"
                + hashlib.sha256(data).hexdigest()[:12]
                + ".json"
            )
        if not p.exists():
            p.write_bytes(data)

        print()
        print("=" * 214)
        print(f"{MILESTONE}: TECHNICAL / AUTHORITY BLOCK")
        print("=" * 214)
        print("Stage    :", stage)
        print("Exception:", repr(exc))
        print("R3-R3-R3 scientific FAIL remains immutable.")
        print("NO DOMAIN EXECUTION, LP, FLOW REFRESH, OR AUTOMATIC RERUN AUTHORIZED.")
        print("=" * 214)
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
    raise SystemExit(main(args.project_root, args.drive_root))
