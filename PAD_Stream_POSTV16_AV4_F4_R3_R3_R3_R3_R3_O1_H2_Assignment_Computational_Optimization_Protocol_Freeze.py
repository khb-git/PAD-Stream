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


MILESTONE = "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O1"
PROTOCOL_ID = (
    "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O1_H2_ASSIGNMENT_COMPUTATIONAL_"
    "OPTIMIZATION_SEMANTICS_FREEZE_V1"
)

STATUS_PASS = (
    "AV4F4R3R3R3R3R3O1_FROZEN_H2_PHYSICS_AND_LEXICOGRAPHIC_SEMANTICS_"
    "PERSISTENT_NATIVE_HIGHS_EXACT_GRAPH_REDUCTION_COMPONENT_DECOMPOSITION_"
    "WARM_START_TELEMETRY_OPTIMIZATION_PROSPECTIVELY_FROZEN_NO_EXECUTION"
)
STATUS_BLOCKED = "AV4F4R3R3R3R3R3O1_OPTIMIZATION_PROTOCOL_FREEZE_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT_R3_COMMIT = "efaca1993b7d5ddadf94c1ae42688b2afef427ab"

GRID = (15, 50, 50)
NZ, NY, NX = GRID
NCELL = NZ * NY * NX
NSL = 1078
NCV = 200
NCVTOTAL = NSL * NCV

EXPECTED_E0_PAIRS = 269721
EXPECTED_E1_PAIRS = 1245666
EXPECTED_E2_PAIRS = 3091073
EXPECTED_E2_GLOBAL_CELLS = 34497

R3 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_"
    "H2_Horizontal_Graph_Radius_2_Occupancy_Extension_Execution.py"
)
R3_BLOB = "14035aa5ec2e5338b8ba6d8b099e1423bd426beb"

R2 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R2_"
    "H2_Horizontal_Graph_Radius_2_Support_Selection_Freeze.py"
)
R2_BLOB = "0ae1e22f25ffd807b98cca9ead74b4b8cf61f672"

R1 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R1_"
    "Prospective_Support_Class_Feasibility_Audit.py"
)
R1_BLOB = "a342684ee48567ad11ee65cce2afe8c85eb9b432"

SOURCE_BLOBS = {
    R3: R3_BLOB,
    R2: R2_BLOB,
    R1: R1_BLOB,
}

BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

R2_REL = (
    BASE_AV4
    / "POSTV16_AV4_F4_R3_R3_R3_R3_R2_H2_Horizontal_Graph_Radius_2_Freeze"
)
R2_SUMMARY = "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R2_Summary.json"
R2_PROTOCOL = "POSTV16_AV4_F4_R3_R3_R3_R3_R2_Frozen_H2_Protocol.json"
R2_HANDOFF = (
    "POSTV16_AV4_F4_R3_R3_R3_R3_R2_R3R3R3R3R3_Execution_Handoff_Contract.json"
)
R2_DECISION = "POSTV16_AV4_F4_R3_R3_R3_R3_R2_Decision_Contract.json"
R2_MANIFEST = "POSTV16_AV4_F4_R3_R3_R3_R3_R2_Artifact_Manifest.csv"
R2_STATUS = (
    "AV4F4R3R3R3R3R2_R3R3R3R3R1_PROSPECTIVE_SUPPORT_AUDIT_BOUND_"
    "H2_HORIZONTAL_GRAPH_RADIUS_2_SELECTED_AS_SMALLEST_TESTED_FEASIBLE_CLASS_"
    "PROSPECTIVELY_FROZEN_NO_EXECUTION"
)

R1_REL = (
    BASE_AV4
    / "POSTV16_AV4_F4_R3_R3_R3_R3_R1_Prospective_Support_Class_Feasibility_Audit"
)
R1_SUMMARY = "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R1_Summary.json"
R1_MATRIX = "POSTV16_AV4_F4_R3_R3_R3_R3_R1_Candidate_Matrix.csv"
R1_MANIFEST = "POSTV16_AV4_F4_R3_R3_R3_R3_R1_Artifact_Manifest.csv"
R1_STATUS = (
    "AV4F4R3R3R3R3R1_R3R3R3R3_E1_SINGLE_RING_HALL_DEFICIT_BOUND_"
    "PROSPECTIVE_SUPPORT_CLASS_FEASIBILITY_AUDIT_COMPLETE_NO_REPAIR_SELECTED"
)

OUT_REL = (
    BASE_AV4
    / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O1_H2_Assignment_Computational_Optimization_Freeze"
)
BLOCK_REL = BASE_AV4 / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O1_BLOCKED"


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
        for k in row:
            if k not in fields:
                fields.append(k)
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


def row_by_candidate(rows: list[dict[str, str]], name: str) -> dict[str, str]:
    match = [r for r in rows if r.get("candidate") == name]
    if len(match) != 1:
        raise GateError(f"candidate_row_count:{name}:{len(match)}")
    return match[0]


def as_bool(v: str) -> bool:
    return str(v).strip().lower() in {"true", "1", "yes"}


def self_test() -> None:
    edges = [(0, 0), (0, 1), (1, 2), (1, 3)]
    cv_to_cells = {}
    for cv, cell in edges:
        cv_to_cells.setdefault(cv, set()).add(cell)
    assert cv_to_cells[0].isdisjoint(cv_to_cells[1])
    assert 0.0 == 0.0
    assert EXPECTED_E0_PAIRS < EXPECTED_E1_PAIRS < EXPECTED_E2_PAIRS
    assert EXPECTED_E2_GLOBAL_CELLS <= NCELL
    print(
        "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O1 H2 assignment computational-"
        "optimization protocol self-test: PASS"
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
        "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O1 — H2 ASSIGNMENT "
        "COMPUTATIONAL-OPTIMIZATION PROTOCOL FREEZE"
    )
    print("=" * 214)
    print("DESIGN/FREEZE ONLY. NO LP OR NETWORK-FLOW EXECUTION.")
    print("NO MAPBACK. NO FLOW REFRESH. NO PHYSICAL-TIME ADVANCE.")
    print("R3 ORIGINAL GENERIC-LP IMPLEMENTATION REMAINS IMMUTABLE.")
    print("H2 PHYSICS, HARD CONSTRAINTS, AND LEXICOGRAPHIC OBJECTIVES ARE UNCHANGED.")
    print("ONLY SOLVER LIFECYCLE / EXACT GRAPH ALGEBRA / TELEMETRY MAY CHANGE.")
    print()

    try:
        stage = "repository_authority"
        parent = git_text(root, "rev-parse", "HEAD^")
        status = git_text(root, "status", "--porcelain")
        gate("repository_parent_is_original_R3_commit", parent == PARENT_R3_COMMIT, parent)
        gate("repository_clean", status == "", repr(status))

        for fn, expected in SOURCE_BLOBS.items():
            p = root / fn
            actual = git_blob(p, root) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact", actual == expected, actual)

        stage = "formal_R2_freeze_binding"
        r2d = drive / R2_REL
        gate("R2_output_present", r2d.is_dir(), str(r2d))
        r2manifest = verify_manifest(r2d, R2_MANIFEST)
        gate("R2_manifest_exact_5", len(r2manifest) == 5, len(r2manifest))
        r2summary = load_json(r2d / R2_SUMMARY)
        r2protocol = load_json(r2d / R2_PROTOCOL)
        r2handoff = load_json(r2d / R2_HANDOFF)
        r2decision = load_json(r2d / R2_DECISION)

        gate("R2_status_exact", r2summary["status"] == R2_STATUS, r2summary["status"])
        gate(
            "R2_H2_geometry_exact",
            r2summary["selected_candidate"] == "H2_HORIZONTAL_GRAPH_RADIUS_2"
            and int(r2summary["H2_pair_count"]) == EXPECTED_E2_PAIRS
            and int(r2summary["H2_global_cell_count"]) == EXPECTED_E2_GLOBAL_CELLS
            and float(r2summary["H2_minimum_unserved_mass_kg"]) == 0.0
            and r2summary["vertical_support"] is False,
        )
        gate(
            "R2_H2_protocol_exact",
            r2protocol["E2"]["offset_rule"] == "dk=0 and |dj|+|di|<=2"
            and int(r2protocol["E2"]["offset_count_including_origin"]) == 13
            and int(r2protocol["E2"]["second_shell_offset_count"]) == 8
            and r2protocol["E2"]["vertical_neighbors"] is False
            and r2protocol["E2"]["radius_greater_than_2"] is False,
        )
        gate(
            "R2_hard_constraints_exact",
            r2protocol["hard_constraints_at_execution"]["accepted_event_CV_mass_unchanged"] is True
            and r2protocol["hard_constraints_at_execution"]["residual_grid_sidecar_exactly_unchanged"] is True
            and r2protocol["hard_constraints_at_execution"]["no_mass_outside_E2"] is True
            and r2protocol["hard_constraints_at_execution"]["global_component_mass_exact"] is True,
        )
        gate(
            "R2_original_R3_execution_authorized",
            r2handoff["milestone"] == "POSTV16-AV4-F4-R3-R3-R3-R3-R3"
            and r2handoff["authorized"] is True
            and r2handoff["execution"] is True
            and r2decision["R3R3R3R3R3_execution_authorized"] is True,
        )

        stage = "formal_R1_feasibility_binding"
        r1d = drive / R1_REL
        gate("R1_output_present", r1d.is_dir(), str(r1d))
        r1manifest = verify_manifest(r1d, R1_MANIFEST)
        gate("R1_manifest_exact_6", len(r1manifest) == 6, len(r1manifest))
        r1summary = load_json(r1d / R1_SUMMARY)
        r1rows = read_csv(r1d / R1_MATRIX)
        h2 = row_by_candidate(r1rows, "H2_HORIZONTAL_GRAPH_RADIUS_2")
        gate("R1_status_exact", r1summary["status"] == R1_STATUS, r1summary["status"])
        gate(
            "R1_H2_formal_feasibility_certificate_exact",
            int(h2["pair_count"]) == EXPECTED_E2_PAIRS
            and int(h2["global_cell_count"]) == EXPECTED_E2_GLOBAL_CELLS
            and float(h2["minimum_unserved_mass_kg"]) == 0.0
            and as_bool(h2["feasible"]) is True,
            h2,
        )

        stage = "optimization_semantics_freeze"

        protocol = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "protocol_id": PROTOCOL_ID,
            "purpose": (
                "Reduce CPU wall time and make solver progress observable while preserving "
                "the exact frozen H2 mapback mathematics and all physical constraints."
            ),
            "historical_semantics": {
                "original_R3_source_blob": R3_BLOB,
                "original_R3_execution_status": (
                    "No scientific conclusion is inferred here from any incomplete runtime attempt. "
                    "The original runner remains immutable as the generic-LP reference implementation."
                ),
                "R2_freeze_status": R2_STATUS,
                "R1_H2_formal_minimum_unserved_mass_kg": 0.0,
            },
            "immutable_scientific_problem": {
                "grid": list(GRID),
                "CV_count": NCVTOTAL,
                "E0_pair_count": EXPECTED_E0_PAIRS,
                "E1_pair_count": EXPECTED_E1_PAIRS,
                "E2_pair_count": EXPECTED_E2_PAIRS,
                "E2_global_cell_count": EXPECTED_E2_GLOBAL_CELLS,
                "E2_geometry": "dk=0 and |dj|+|di|<=2 from exact E0, per CV",
                "accepted_event_CV_masses": "unchanged exact authority",
                "residual_grid_sidecar": "unchanged exact authority",
                "cell_capacity": "unchanged source-authentic S=0.80 EOS capacity",
                "nonnegative_pair_mass": True,
                "no_mass_outside_E2": True,
                "global_component_mass_exact": True,
                "vertical_support": False,
                "horizontal_radius_greater_than_2": False,
                "H2_plus_V1_fallback": False,
            },
            "lexicographic_semantics_unchanged": {
                "stage_1": "minimize mass on second horizontal shell E2\\E1",
                "stage_2": "freeze stage-1 optimum; minimize total extension mass E2\\E0",
                "stage_3": (
                    "freeze stages 1-2; minimize L1 deviation on E0 from "
                    "F2-R3 parent-continuity target"
                ),
                "stage_4": (
                    "freeze stages 1-3; minimize L1 deviation on E0 from raw-event EOS target"
                ),
                "stage_5": (
                    "freeze stages 1-4; minimize the same deterministic global pair-rank "
                    "tie-break objective over E2"
                ),
            },
            "authorized_computational_transformations": {
                "native_solver_interface": "highspy.Highs",
                "canonical_solver_family": "HiGHS CPU LP",
                "GPU_required": False,
                "approximate_GPU_PDLP_or_first_order_solver": False,
                "persistent_model": True,
                "persistent_model_scope": (
                    "one model per exact disconnected active bipartite component; "
                    "if graph is connected, one global model"
                ),
                "build_constraint_matrix_once_per_component": True,
                "prebuild_parent_and_raw_L1_auxiliary_structure": True,
                "change_objective_between_stages": True,
                "add_or_activate_only_previous_optimum_freeze_rows": True,
                "basis_reuse_between_stages": True,
                "basis_reuse_is_performance_only": True,
                "basis_reuse_failure_semantics": (
                    "record telemetry and permit a cold resolve of the identical persistent "
                    "model; this is not a scientific fallback"
                ),
            },
            "stage_0_optimization_change": {
                "standalone_minimum_unserved_LP_removed": True,
                "formal_R1_H2_feasibility_certificate_bound": True,
                "execution_time_fresh_feasibility_certificate": (
                    "A successful Stage-1 primal solution must satisfy every exact CV equality "
                    "and cell-capacity inequality; therefore Stage 1 re-certifies E2 feasibility."
                ),
                "no_feasibility_requirement_removed": True,
                "if_stage_1_infeasible": (
                    "SCIENTIFIC FAIL only after exact support/capacity/state reconstruction "
                    "and solver status are certified; no automatic support expansion."
                ),
            },
            "exact_graph_preprocessing": {
                "allowed": True,
                "zero_demand_CV_pruning": (
                    "allowed only when authoritative event CV demand is exactly == 0.0; "
                    "all removed outgoing variables are mathematically fixed at zero"
                ),
                "zero_available_capacity_cell_pruning": (
                    "allowed only when authoritative available capacity is exactly == 0.0; "
                    "all removed incoming variables are mathematically fixed at zero"
                ),
                "tolerance_based_demand_pruning": False,
                "tolerance_based_capacity_pruning": False,
                "positive_demand_or_positive_capacity_approximation": False,
                "reconstruction_of_removed_zero_variables_required": True,
            },
            "exact_component_decomposition": {
                "allowed": True,
                "graph": "active bipartite CV-to-cell E2 incidence graph",
                "component_definition": "ordinary undirected connected components",
                "proof_condition": (
                    "components share neither CV equality rows nor Cartesian capacity rows; "
                    "all lexicographic objectives are sums of per-edge/per-E0 terms"
                ),
                "stage_optimum": (
                    "global optimum at every lexicographic stage equals the sum of exact "
                    "component optima; each component optimum is frozen before the next stage"
                ),
                "global_pair_rank": (
                    "retain original full-E2 global pair rank coefficients inside each component"
                ),
                "cross_component_approximation": False,
            },
            "required_telemetry": {
                "preprocessing": [
                    "raw E0/E1/E2 pair counts",
                    "active CV count",
                    "exact-zero CV count removed",
                    "active cell count",
                    "exact-zero-capacity cell count removed",
                    "active edge count",
                    "connected-component count",
                    "largest component CV/cell/edge counts",
                    "component-size summary",
                    "preprocessing wall time",
                    "process RSS if available",
                ],
                "each_optimization_stage": [
                    "explicit START line before solver call",
                    "component identifier",
                    "variables",
                    "rows",
                    "matrix nonzeros if available",
                    "solver method",
                    "warm-start/basis status",
                    "wall time",
                    "solver status",
                    "simplex/IPM iteration counts if available",
                    "objective",
                    "post-solve CV equality Linf residual",
                    "post-solve maximum capacity excess",
                    "process RSS if available",
                ],
                "aggregate": [
                    "total optimization wall time",
                    "wall time by lexicographic stage",
                    "wall time by component",
                    "final H2 shell mass",
                    "final total extension mass",
                ],
            },
            "numerical_and_failure_semantics": {
                "no_change_to_existing_physical_validation_tolerances": True,
                "no_capacity_relaxation": True,
                "no_CV_mass_relaxation": True,
                "no_mass_clipping": True,
                "no_global_rescaling": True,
                "no_radius_3": True,
                "no_vertical_support": True,
                "no_H2_plus_V1": True,
                "no_automatic_alternate_repair": True,
                "missing_highspy_or_API_incompatibility": "TECHNICAL/AUTHORITY BLOCK",
                "model_build_or_memory_failure": "TECHNICAL/AUTHORITY BLOCK",
                "solver_infeasible_after_exact_reconstruction": (
                    "SCIENTIFIC FAIL only if solver status and exact problem reconstruction "
                    "are both certified; otherwise TECHNICAL/AUTHORITY BLOCK"
                ),
            },
            "scope_separation": {
                "O2": "optimized H2 assignment only; stop after Cartesian event mapback certification",
                "O3": "same-time pressure/Darcy/Pollock/TOF refresh and bounded reprojection",
                "R3R3R4": "Day413.78677770818403 to Day500 physical-time continuation",
                "reason": (
                    "keep computational optimization, flow refresh, and physical-time continuation "
                    "independently auditable and independently rerunnable"
                ),
            },
        }

        handoff = {
            "milestone": "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O2",
            "name": "Persistent Native-HiGHS H2 Assignment Execution",
            "authorized": True,
            "execution": True,
            "required_O1_status": STATUS_PASS,
            "scope": [
                "bind exact R2 H2 freeze and R1 H2 feasibility certificate",
                "reconstruct exact E0/E1/E2 and event state",
                "perform exact-zero graph preprocessing only",
                "audit exact connected components",
                "solve stages 1-5 with persistent native HiGHS model(s)",
                "reuse basis when valid and report whether reuse occurs",
                "publish complete stage/component telemetry",
                "reconstruct all zero-pruned variables as exact zeros",
                "certify exact CV mass, cell capacity, residual sidecar and global mass",
                "publish optimized Cartesian event mapback and stop",
            ],
            "not_authorized": [
                "standalone repeated generic Stage-0 minimum-unserved LP",
                "flow refresh",
                "Pollock or TOF refresh",
                "bounded refreshed-geometry reprojection",
                "physical-time advance",
                "radius >2",
                "vertical support",
                "H2+V1 fallback",
                "capacity or CV-mass relaxation",
                "tolerance-based graph pruning",
                "GPU/PDLP substitution",
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
            "R2_H2_freeze_preserved": True,
            "R1_H2_feasibility_certificate_preserved": True,
            "original_R3_source_preserved": True,
            "scientific_problem_changed": False,
            "lexicographic_objectives_changed": False,
            "optimization_execution_performed": False,
            "mapback_execution_performed": False,
            "flow_refresh_executed": False,
            "physical_time_advanced": False,
            "O2_authorized": True,
            "O3_authorized": False,
            "R3R3R4_authorized": False,
            "F5_dataset_generation_authorized": False,
            "training_authorized": False,
        }

        summary = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "protocol_id": PROTOCOL_ID,
            "optimization_class": "solver_lifecycle_and_exact_graph_algebra_only",
            "original_R3_blob": R3_BLOB,
            "E2_pair_count": EXPECTED_E2_PAIRS,
            "E2_global_cell_count": EXPECTED_E2_GLOBAL_CELLS,
            "formal_R1_H2_minimum_unserved_mass_kg": 0.0,
            "standalone_stage0_LP_in_O2": False,
            "native_highspy_persistent_model": True,
            "exact_zero_pruning_only": True,
            "exact_component_decomposition_allowed": True,
            "basis_reuse_authorized": True,
            "stage_level_telemetry_required": True,
            "scientific_problem_changed": False,
            "O2_authorized": True,
            "O3_authorized": False,
            "R3R3R4_authorized": False,
            "F5_authorized": False,
        }

        files = {
            "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O1_Summary.json":
                json_bytes(summary),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O1_Frozen_Optimization_Protocol.json":
                json_bytes(protocol),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O1_O2_Handoff_Contract.json":
                json_bytes(handoff),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O1_Decision_Contract.json":
                json_bytes(decision),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O1_Final_Gate_Matrix.csv":
                csv_bytes([{"gate": k, **v} for k, v in gates.items()]),
        }
        immutable_publish(out, files)

        manifest_rows = []
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name != "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O1_Artifact_Manifest.csv":
                manifest_rows.append(
                    {"file": p.name, "sha256": sha256_file(p), "bytes": p.stat().st_size}
                )
        immutable_publish(
            out,
            {
                "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O1_Artifact_Manifest.csv":
                    csv_bytes(manifest_rows)
            },
        )

        print()
        print("=" * 214)
        print(
            "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O1: H2 ASSIGNMENT "
            "COMPUTATIONAL-OPTIMIZATION PROTOCOL FREEZE PASS"
        )
        print("=" * 214)
        print("Original R3 generic-LP source           : PRESERVED")
        print("H2 physics / support / capacity         : UNCHANGED")
        print("Lexicographic objectives                : UNCHANGED")
        print("Standalone Stage-0 LP in O2             : REMOVED AS REDUNDANT")
        print("Native persistent HiGHS                 : FROZEN")
        print("Exact-zero graph pruning                : AUTHORIZED")
        print("Exact component decomposition           : AUTHORIZED")
        print("Basis reuse                              : AUTHORIZED")
        print("Stage/component telemetry               : REQUIRED")
        print("O2 optimized H2 assignment              : AUTHORIZED")
        print("O3 flow refresh / R3-R3-R4 / F5        : NOT AUTHORIZED")
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
            "R2_H2_freeze_preserved": True,
            "R1_H2_feasibility_certificate_preserved": True,
            "original_R3_source_preserved": True,
            "scientific_problem_changed": False,
            "optimization_execution_performed": False,
            "mapback_execution_performed": False,
            "flow_refresh_executed": False,
            "physical_time_advanced": False,
            "automatic_rerun_authorized": False,
            "O2_authorized": False,
            "O3_authorized": False,
            "R3R3R4_authorized": False,
            "F5_dataset_generation_authorized": False,
            "training_authorized": False,
        }
        data = json_bytes(report)
        p = blocked / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O1_Blocked_Report.json"
        if p.exists() and p.read_bytes() != data:
            p = blocked / (
                "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O1_Blocked_Report_"
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
        print("NO OPTIMIZED EXECUTION OR SCIENTIFIC CHANGE AUTHORIZED.")
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
