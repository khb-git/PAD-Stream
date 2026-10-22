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


MILESTONE = "POSTV16-AV4-F4-R3-R3-R3-R3-R2"
PROTOCOL_ID = (
    "POSTV16_AV4_F4_R3_R3_R3_R3_R2_SINGLE_NONRECURSIVE_PER_CV_"
    "HORIZONTAL_GRAPH_RADIUS_2_OCCUPANCY_EXTENSION_V1"
)

STATUS_PASS = (
    "AV4F4R3R3R3R3R2_R3R3R3R3R1_PROSPECTIVE_SUPPORT_AUDIT_BOUND_"
    "H2_HORIZONTAL_GRAPH_RADIUS_2_SELECTED_AS_SMALLEST_TESTED_FEASIBLE_CLASS_"
    "PROSPECTIVELY_FROZEN_NO_EXECUTION"
)
STATUS_BLOCKED = "AV4F4R3R3R3R3R2_H2_SUPPORT_SELECTION_FREEZE_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT_R1_COMMIT = "236b469b1ef656361302e39ae6e515aa8f7ef258"

# Formal R1 candidate-matrix values.
H1_PAIR_COUNT = 1245666
H1_GLOBAL_CELL_COUNT = 31016
H1_MIN_UNSERVED_KG = 563162.189227371

H2_PAIR_COUNT = 3091073
H2_GLOBAL_CELL_COUNT = 34497
H2_MIN_UNSERVED_KG = 0.0

H1V1_PAIR_COUNT = 1746842
H1V1_GLOBAL_CELL_COUNT = 33352
H1V1_MIN_UNSERVED_KG = 48010.94561431022

H2V1_PAIR_COUNT = 3591810
H2V1_GLOBAL_CELL_COUNT = 35293
H2V1_MIN_UNSERVED_KG = 0.0

SELECTED = "H2_HORIZONTAL_GRAPH_RADIUS_2"

R1 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R1_"
    "Prospective_Support_Class_Feasibility_Audit.py"
)
R1_BLOB = "a342684ee48567ad11ee65cce2afe8c85eb9b432"

R3R3R3R3 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_"
    "Per_CV_Horizontal_Face_Occupancy_Extension_Execution.py"
)
R3R3R3R3_BLOB = "a20a31bd48d4331b50dc71488ceaa5dc611acf25"

R3R3R3R2 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R2_"
    "Per_CV_Horizontal_Face_Occupancy_Extension_Freeze.py"
)
R3R3R3R2_BLOB = "3768e7b2793b959be83629bc3299e81353ca4af2"

SOURCE_BLOBS = {
    R1: R1_BLOB,
    R3R3R3R3: R3R3R3R3_BLOB,
    R3R3R3R2: R3R3R3R2_BLOB,
}

BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

R1_REL = (
    BASE_AV4
    / "POSTV16_AV4_F4_R3_R3_R3_R3_R1_Prospective_Support_Class_Feasibility_Audit"
)
R1_SUMMARY = "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R1_Summary.json"
R1_DIAG = "POSTV16_AV4_F4_R3_R3_R3_R3_R1_Prospective_Support_Feasibility_Diagnosis.json"
R1_MATRIX = "POSTV16_AV4_F4_R3_R3_R3_R3_R1_Candidate_Matrix.csv"
R1_HANDOFF = "POSTV16_AV4_F4_R3_R3_R3_R3_R1_R3R3R3R3R2_Handoff_Contract.json"
R1_DECISION = "POSTV16_AV4_F4_R3_R3_R3_R3_R1_Decision_Contract.json"
R1_MANIFEST = "POSTV16_AV4_F4_R3_R3_R3_R3_R1_Artifact_Manifest.csv"

R1_STATUS = (
    "AV4F4R3R3R3R3R1_R3R3R3R3_E1_SINGLE_RING_HALL_DEFICIT_BOUND_"
    "PROSPECTIVE_SUPPORT_CLASS_FEASIBILITY_AUDIT_COMPLETE_NO_REPAIR_SELECTED"
)

OUT_REL = (
    BASE_AV4
    / "POSTV16_AV4_F4_R3_R3_R3_R3_R2_H2_Horizontal_Graph_Radius_2_Freeze"
)
BLOCK_REL = BASE_AV4 / "POSTV16_AV4_F4_R3_R3_R3_R3_R2_BLOCKED"


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


def near(a: Any, b: Any, rtol: float = 1e-11, atol: float = 1e-6) -> bool:
    aa = float(a)
    bb = float(b)
    return abs(aa - bb) <= max(atol, rtol * max(abs(bb), 1.0))


def bool_from_csv(v: str) -> bool:
    return str(v).strip().lower() in {"true", "1", "yes"}


def row_by_candidate(rows: list[dict[str, str]], name: str) -> dict[str, str]:
    match = [r for r in rows if r.get("candidate") == name]
    if len(match) != 1:
        raise GateError(f"candidate_row_count:{name}:{len(match)}")
    return match[0]


def self_test() -> None:
    # Frozen H2 graph-radius definition in a horizontal Cartesian layer:
    # all offsets with |dj| + |di| <= 2 and dk == 0.
    offsets = [
        (0, dj, di)
        for dj in range(-2, 3)
        for di in range(-2, 3)
        if abs(dj) + abs(di) <= 2
    ]
    assert len(offsets) == 13
    assert all(dk == 0 for dk, _, _ in offsets)
    assert (0, 2, 0) in offsets
    assert (0, 1, 1) in offsets
    assert (0, 2, 1) not in offsets
    assert (1, 0, 0) not in offsets

    # Shell partition.
    h1 = {(0, dj, di) for dj, di in [(0,0),(0,-1),(0,1),(-1,0),(1,0)]}
    h2_shell = set(offsets) - h1
    assert len(h2_shell) == 8

    print(
        "POSTV16-AV4-F4-R3-R3-R3-R3-R2 H2 horizontal graph-radius-2 "
        "selection/freeze self-test: PASS"
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
        "POSTV16-AV4-F4-R3-R3-R3-R3-R2 — H2 HORIZONTAL GRAPH-RADIUS-2 "
        "SUPPORT-SELECTION / DESIGN FREEZE"
    )
    print("=" * 214)
    print("DESIGN / FREEZE ONLY. NO LP EXECUTION. NO MAPBACK EXECUTION.")
    print("R3-R3-R3-R3 SCIENTIFIC FAIL REMAINS IMMUTABLE.")
    print("ONE SELECTED CANDIDATE: H2 HORIZONTAL GRAPH RADIUS 2 FROM EXACT E0.")
    print("NO VERTICAL SUPPORT. NO GRAPH RADIUS >2. NO CAPACITY OR MASS RELAXATION.")
    print("NO FLOW REFRESH. NO PHYSICAL-TIME ADVANCE. NO R3-R3-R4. NO F5.")
    print()

    try:
        stage = "repository_authority"
        parent = git_text(root, "rev-parse", "HEAD^")
        status = git_text(root, "status", "--porcelain")
        gate("repository_parent_is_R1_commit", parent == PARENT_R1_COMMIT, parent)
        gate("repository_clean", status == "", repr(status))
        for fn, expected in SOURCE_BLOBS.items():
            p = root / fn
            actual = git_blob(p, root) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact", actual == expected, actual)

        stage = "R1_authority_binding"
        d = drive / R1_REL
        gate("R1_output_present", d.is_dir(), str(d))
        manifest = verify_manifest(d, R1_MANIFEST)
        gate("R1_manifest_exact_6", len(manifest) == 6, len(manifest))

        summary = load_json(d / R1_SUMMARY)
        diag = load_json(d / R1_DIAG)
        handoff = load_json(d / R1_HANDOFF)
        decision_in = load_json(d / R1_DECISION)
        rows = read_csv(d / R1_MATRIX)

        gate("R1_status_exact", summary["status"] == R1_STATUS, summary["status"])
        gate(
            "R1_classification_exact",
            summary["classification"] == "AT_LEAST_ONE_PROSPECTIVE_EXTENSION_CLASS_FEASIBLE",
            summary["classification"],
        )
        gate(
            "R1_diagnostic_best_exact",
            summary["diagnostic_best_candidate_by_feasibility_deficit_support_size"] == SELECTED,
            summary["diagnostic_best_candidate_by_feasibility_deficit_support_size"],
        )
        gate(
            "R1_no_repair_selected",
            summary["repair_selected"] is False
            and decision_in["repair_selected"] is False
            and decision_in["repair_execution_performed"] is False
            and decision_in["support_domain_changed"] is False,
        )
        gate(
            "R1_handoff_design_only",
            handoff["milestone"] == MILESTONE
            and handoff["authorized"] is True
            and handoff["execution"] is False
            and handoff["repair_execution_authorized"] is False,
        )

        h1 = row_by_candidate(rows, "H1_REPRODUCTION")
        h2 = row_by_candidate(rows, "H2_HORIZONTAL_GRAPH_RADIUS_2")
        h1v1 = row_by_candidate(rows, "H1_PLUS_V1_DIRECT_3D_FACE_RING")
        h2v1 = row_by_candidate(rows, "H2_PLUS_V1")

        gate(
            "R1_H1_exact_infeasible",
            int(h1["pair_count"]) == H1_PAIR_COUNT
            and int(h1["global_cell_count"]) == H1_GLOBAL_CELL_COUNT
            and near(h1["minimum_unserved_mass_kg"], H1_MIN_UNSERVED_KG)
            and bool_from_csv(h1["feasible"]) is False,
            h1,
        )
        gate(
            "R1_H2_exact_feasible",
            int(h2["pair_count"]) == H2_PAIR_COUNT
            and int(h2["global_cell_count"]) == H2_GLOBAL_CELL_COUNT
            and near(h2["minimum_unserved_mass_kg"], H2_MIN_UNSERVED_KG)
            and bool_from_csv(h2["feasible"]) is True,
            h2,
        )
        gate(
            "R1_H1V1_exact_infeasible",
            int(h1v1["pair_count"]) == H1V1_PAIR_COUNT
            and int(h1v1["global_cell_count"]) == H1V1_GLOBAL_CELL_COUNT
            and near(h1v1["minimum_unserved_mass_kg"], H1V1_MIN_UNSERVED_KG)
            and bool_from_csv(h1v1["feasible"]) is False,
            h1v1,
        )
        gate(
            "R1_H2V1_exact_feasible",
            int(h2v1["pair_count"]) == H2V1_PAIR_COUNT
            and int(h2v1["global_cell_count"]) == H2V1_GLOBAL_CELL_COUNT
            and near(h2v1["minimum_unserved_mass_kg"], H2V1_MIN_UNSERVED_KG)
            and bool_from_csv(h2v1["feasible"]) is True,
            h2v1,
        )
        gate(
            "H2_is_smallest_tested_feasible_support_class",
            bool_from_csv(h2["feasible"])
            and bool_from_csv(h2v1["feasible"])
            and not bool_from_csv(h1v1["feasible"])
            and int(h2["pair_count"]) < int(h2v1["pair_count"])
            and int(h2["global_cell_count"]) < int(h2v1["global_cell_count"]),
            {
                "H2_pairs": int(h2["pair_count"]),
                "H2_cells": int(h2["global_cell_count"]),
                "H2V1_pairs": int(h2v1["pair_count"]),
                "H2V1_cells": int(h2v1["global_cell_count"]),
            },
        )

        stage = "freeze_H2_protocol"

        protocol = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "protocol_id": PROTOCOL_ID,
            "selected_candidate": SELECTED,
            "selection_basis": {
                "H1_infeasible_minimum_unserved_kg": H1_MIN_UNSERVED_KG,
                "H1_plus_V1_infeasible_minimum_unserved_kg": H1V1_MIN_UNSERVED_KG,
                "H2_feasible_minimum_unserved_kg": H2_MIN_UNSERVED_KG,
                "H2_plus_V1_feasible_minimum_unserved_kg": H2V1_MIN_UNSERVED_KG,
                "reason": (
                    "H2 is the smallest tested feasible support class. "
                    "H1+V1 is smaller but remains infeasible; H2+V1 is feasible "
                    "but strictly larger and introduces unnecessary vertical reach."
                ),
            },
            "E0": {
                "definition":
                    "exact frozen SG7D/E37A per-CV Cartesian incidence used by R3-R3-R3",
            },
            "E1": {
                "definition":
                    "all same-layer offsets from E0 with horizontal Manhattan distance <=1",
                "historical_pair_count": H1_PAIR_COUNT,
                "historical_result": "INFEASIBLE",
            },
            "E2": {
                "definition": (
                    "For each CV independently, union of all in-bounds cells whose "
                    "same-layer Cartesian horizontal Manhattan graph distance from "
                    "any exact E0 cell is <=2."
                ),
                "offset_rule": "dk=0 and |dj|+|di|<=2",
                "offset_count_including_origin": 13,
                "second_shell_offset_count": 8,
                "pair_count_from_formal_audit": H2_PAIR_COUNT,
                "global_cell_count_from_formal_audit": H2_GLOBAL_CELL_COUNT,
                "formal_minimum_unserved_mass_kg": 0.0,
                "nonrecursive_runtime_growth": True,
                "graph_radius_fixed_at_2": True,
                "vertical_neighbors": False,
                "diagonal_3D_neighbors": False,
                "horizontal_diagonal_cells_at_manhattan_distance_2": True,
                "radius_greater_than_2": False,
                "extension_cell_role": "terminal occupancy sink only",
                "extension_cell_becomes_transport_CV": False,
            },
            "hard_constraints_at_execution": {
                "accepted_event_CV_mass_unchanged": True,
                "per_CV_mass_exact":
                    "sum_{c in E2_j} x_jc = M_event_j for every CV j",
                "nonnegative_pair_mass": "x_jc >= 0",
                "cell_capacity":
                    "R_c + sum_j x_jc <= C_c for every Cartesian cell c",
                "residual_grid_sidecar_exactly_unchanged": True,
                "source_authentic_Smax_capacity": "S=0.80 EOS capacity under pre-refresh pressure",
                "no_mass_outside_E2": True,
                "global_component_mass_exact": True,
            },
            "lexicographic_objectives_at_execution": {
                "stage_0":
                    "reproduce exact E2 feasibility with minimum-unserved mass = 0",
                "stage_1":
                    "minimize mass assigned to second horizontal shell E2\\E1",
                "stage_2":
                    "freeze stage-1 optimum and minimize total extension mass E2\\E0",
                "stage_3":
                    "freeze stages 1-2 and minimize L1 deviation on E0 from F2-R3 parent-continuity target",
                "stage_4":
                    "freeze stages 1-3 and minimize L1 deviation on E0 from raw event EOS target",
                "stage_5":
                    "freeze stages 1-4 and apply deterministic lexicographic pair-rank tie break",
                "physical_meaning": (
                    "Use the least possible second-ring mass; then the least total "
                    "off-E0 mass; only then optimize ownership continuity."
                ),
            },
            "mandatory_execution_diagnostics": {
                "E0_pair_count": True,
                "E1_pair_count": True,
                "E2_pair_count": True,
                "E2_global_cell_count": True,
                "minimum_H2_shell_mass_kg": True,
                "minimum_total_extension_mass_kg": True,
                "CVs_using_H2_shell": True,
                "streamlines_using_H2_shell": True,
                "cells_receiving_H2_shell_mass": True,
                "CVs_using_any_extension": True,
                "all_CV_equalities": True,
                "all_cell_capacity_inequalities": True,
                "outside_E2_mass_exact_zero": True,
            },
            "failure_semantics": {
                "if_E2_reproduction_infeasible":
                    "SCIENTIFIC FAIL; no automatic radius-3 or vertical fallback",
                "automatic_radius_3": False,
                "automatic_vertical_extension": False,
                "automatic_H2_plus_V1": False,
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
        }

        handoff_out = {
            "milestone": "POSTV16-AV4-F4-R3-R3-R3-R3-R3",
            "name":
                "Controlled H2 Horizontal Graph-Radius-2 Occupancy Extension Execution",
            "authorized": True,
            "execution": True,
            "required_R2_status": STATUS_PASS,
            "selected_candidate": SELECTED,
            "scope": [
                "construct exact fixed E2 support with dk=0 and |dj|+|di|<=2 from E0",
                "reproduce E2 zero minimum-unserved mass",
                "execute frozen six-stage lexicographic assignment",
                "certify exact CV mass and Cartesian capacity",
                "execute one same-time event flow refresh",
                "execute bounded refreshed-geometry reprojection",
                "publish refreshed event recurrent state and stop",
            ],
            "not_authorized": [
                "horizontal radius >2",
                "vertical support",
                "H2+V1 fallback",
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
            "R3R3R3R3_scientific_FAIL_preserved": True,
            "R1_prospective_audit_bound": True,
            "selected_candidate": SELECTED,
            "candidate_execution_performed": False,
            "LP_execution_performed": False,
            "support_domain_changed_in_freeze": False,
            "vertical_support_selected": False,
            "radius_greater_than_2_selected": False,
            "capacity_relaxed": False,
            "per_CV_mass_relaxed": False,
            "flow_refresh_executed": False,
            "physical_time_advanced": False,
            "R3R3R3R3R3_execution_authorized": True,
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
            "selected_candidate": SELECTED,
            "H1_minimum_unserved_mass_kg": H1_MIN_UNSERVED_KG,
            "H1_plus_V1_minimum_unserved_mass_kg": H1V1_MIN_UNSERVED_KG,
            "H2_minimum_unserved_mass_kg": H2_MIN_UNSERVED_KG,
            "H2_plus_V1_minimum_unserved_mass_kg": H2V1_MIN_UNSERVED_KG,
            "H2_pair_count": H2_PAIR_COUNT,
            "H2_global_cell_count": H2_GLOBAL_CELL_COUNT,
            "candidate_execution_performed": False,
            "horizontal_graph_radius": 2,
            "vertical_support": False,
            "R3R3R3R3R3_authorized": True,
            "R3R3R4_authorized": False,
            "F5_authorized": False,
        }

        files = {
            "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R2_Summary.json":
                json_bytes(summary_out),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R2_Frozen_H2_Protocol.json":
                json_bytes(protocol),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R2_R3R3R3R3R3_Execution_Handoff_Contract.json":
                json_bytes(handoff_out),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R2_Decision_Contract.json":
                json_bytes(decision),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R2_Final_Gate_Matrix.csv":
                csv_bytes([{"gate": k, **v} for k, v in gates.items()]),
        }
        immutable_publish(out, files)

        manifest_rows = []
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name != "POSTV16_AV4_F4_R3_R3_R3_R3_R2_Artifact_Manifest.csv":
                manifest_rows.append(
                    {"file": p.name, "sha256": sha256_file(p), "bytes": p.stat().st_size}
                )
        immutable_publish(
            out,
            {
                "POSTV16_AV4_F4_R3_R3_R3_R3_R2_Artifact_Manifest.csv":
                    csv_bytes(manifest_rows)
            },
        )

        print()
        print("=" * 214)
        print(
            "POSTV16-AV4-F4-R3-R3-R3-R3-R2: H2 HORIZONTAL GRAPH-RADIUS-2 "
            "SUPPORT-SELECTION / DESIGN FREEZE PASS"
        )
        print("=" * 214)
        print("R3-R3-R3-R3 scientific FAIL             : PRESERVED")
        print("H1 minimum unassignable mass kg          :", H1_MIN_UNSERVED_KG)
        print("H1+V1 minimum unassignable mass kg       :", H1V1_MIN_UNSERVED_KG)
        print("H2 minimum unassignable mass kg          :", H2_MIN_UNSERVED_KG)
        print("H2+V1 minimum unassignable mass kg       :", H2V1_MIN_UNSERVED_KG)
        print("Selected support class                   :", SELECTED)
        print("H2 pair / global-cell count              :", H2_PAIR_COUNT, "/", H2_GLOBAL_CELL_COUNT)
        print("Vertical support                         : False")
        print("LP / mapback execution in R2             : False / False")
        print("POSTV16-AV4-F4-R3-R3-R3-R3-R3          : AUTHORIZED")
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
            "R3R3R3R3_scientific_FAIL_preserved": True,
            "candidate_execution_performed": False,
            "LP_execution_performed": False,
            "support_domain_changed": False,
            "flow_refresh_executed": False,
            "physical_time_advanced": False,
            "automatic_rerun_authorized": False,
            "R3R3R3R3R3_execution_authorized": False,
            "R3R3R4_authorized": False,
            "F5_dataset_generation_authorized": False,
            "training_authorized": False,
        }
        data = json_bytes(report)
        p = blocked / "POSTV16_AV4_F4_R3_R3_R3_R3_R2_Blocked_Report.json"
        if p.exists() and p.read_bytes() != data:
            p = blocked / (
                "POSTV16_AV4_F4_R3_R3_R3_R3_R2_Blocked_Report_"
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
        print("R3-R3-R3-R3 scientific FAIL remains immutable.")
        print("NO H2 EXECUTION, MAPBACK, FLOW REFRESH, OR AUTOMATIC RERUN AUTHORIZED.")
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
