#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

MILESTONE = "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R6-R3"
STATUS_PASS = (
    "AV4F4R3R3R3R3R3O3R6R3_ADAPTIVE_FEASIBILITY_PRESERVING_STABILIZATION_"
    "SEMANTICS_DESIGN_FREEZE_PASS_NO_STABILIZED_EXECUTION_NO_STATE_MUTATION_"
    "NO_SUPPORT_EXPANSION_NO_TIME_ADVANCE"
)
STATUS_BLOCK = "AV4F4R3R3R3R3R3O3R6R3_TECHNICAL_OR_AUTHORITY_BLOCK"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT_COMMIT = "f68b29ecd3580c9fe2344e884de5bd1bd579b1e5"
R2R2_RUNNER = "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R2R2_R2_Block_Report_Filename_Authority_Repair_and_Boundary_Audit.py"
R2R2_BLOB = "8e9720d269a1dc0830f52338399dc0cd7e4c50fd"

BASE = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

R2R2_OUT = BASE / (
    "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R2R2_"
    "Coupled_Map_Feasible_Region_Boundary_Audit"
)
R2R2_POINTS = BASE / (
    "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R2R2_"
    "Boundary_Audit_Point_Checkpoints"
)
R2R2_SUMMARY = "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R2R2_Summary.json"
R2R2_AUDIT = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R2R2_Boundary_Audit.json"
R2R2_POINTS_CSV = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R2R2_Boundary_Points.csv"
R2R2_CV_CSV = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R2R2_Controlling_CV_Diagnostics.csv"
R2R2_DESIGN = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R2R2_Prospective_Stabilization_Design.json"
R2R2_DECISION = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R2R2_Decision_Contract.json"
R2R2_GATES = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R2R2_Final_Gate_Matrix.csv"
R2R2_MANIFEST = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R2R2_Artifact_Manifest.csv"
EXPECTED_R2R2_PAYLOADS = {
    R2R2_SUMMARY,
    R2R2_AUDIT,
    R2R2_POINTS_CSV,
    R2R2_CV_CSV,
    R2R2_DESIGN,
    R2R2_DECISION,
    R2R2_GATES,
}

OUT = BASE / (
    "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R3_"
    "Adaptive_Feasibility_Preserving_Stabilization_Semantics_Design_Freeze"
)
BLOCK = BASE / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R3_BLOCKED"

BOUNDARY_DEN = 1024
FIRST_FEASIBLE_INDEX = 147
FIRST_INFEASIBLE_INDEX = 148
FIRST_FEASIBLE_OMEGA = FIRST_FEASIBLE_INDEX / BOUNDARY_DEN
FIRST_INFEASIBLE_OMEGA = FIRST_INFEASIBLE_INDEX / BOUNDARY_DEN
FIRST_INFEASIBLE_UNSERVED_KG = 0.06022307779858238
P2_UNSERVED_KG = 52.01929485429173
P2_CONTROLLING_CV = 60424

MAX_NONLINEAR_ITERATIONS = 100
PRESSURE_REL_L2_TOL = 1.0e-10
SATURATION_FIXED_POINT_LINF_TOL = 1.0e-10
PRESSURE_LINEAR_REL_RESIDUAL_MAX = 1.0e-8
GLOBAL_MASS_REL_TOL = 1.0e-10
FEASIBILITY_UNSERVED_TOL_KG = 1.0e-6
FEASIBILITY_CV_LINF_TOL_KG = 1.0e-6
FEASIBILITY_CAPACITY_EXCESS_TOL_KG = 1.0e-6
LINE_SEARCH_DENOMINATOR = 1024
MIN_POSITIVE_OMEGA = 1.0 / LINE_SEARCH_DENOMINATOR

class GateError(RuntimeError):
    pass

def git_text(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True, text=True, capture_output=True
    ).stdout.strip()

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def verify_manifest(directory: Path, name: str) -> dict[str, str]:
    p = directory / name
    if not p.is_file():
        raise GateError("manifest_missing:" + str(p))
    rows = read_csv(p)
    if not rows:
        raise GateError("manifest_empty:" + name)
    out: dict[str, str] = {}
    for row in rows:
        fp = directory / row["file"]
        if not fp.is_file():
            raise GateError("manifest_payload_missing:" + row["file"])
        actual = sha256_file(fp)
        if actual != row["sha256"]:
            raise GateError("manifest_sha_mismatch:" + row["file"])
        out[row["file"]] = actual
    return out

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
    import io
    s = io.StringIO(newline="")
    w = csv.DictWriter(s, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return s.getvalue().encode("utf-8")

def immutable_publish(directory: Path, files: dict[str, bytes]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        p = directory / name
        if p.exists() and p.read_bytes() != data:
            raise GateError("existing_output_differs:" + name)
        if not p.exists():
            p.write_bytes(data)

def point_names(index: int) -> tuple[str, str, str]:
    stem = (
        "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R2R2_"
        f"Omega_{index:04d}_of_{BOUNDARY_DEN}"
    )
    return stem + "_State.npz", stem + "_Result.json", stem + "_Manifest.csv"

def point_dir(root: Path, index: int) -> Path:
    return root / f"omega_{index:04d}_of_{BOUNDARY_DEN}"

def self_test() -> None:
    assert len(PARENT_COMMIT) == 40
    assert len(R2R2_BLOB) == 40
    assert BOUNDARY_DEN == 1024
    assert FIRST_FEASIBLE_INDEX == 147
    assert FIRST_INFEASIBLE_INDEX == 148
    assert FIRST_INFEASIBLE_INDEX - FIRST_FEASIBLE_INDEX == 1
    assert MAX_NONLINEAR_ITERATIONS == 100
    assert LINE_SEARCH_DENOMINATOR == 1024
    assert MIN_POSITIVE_OMEGA == 1.0 / 1024.0
    print(
        "POSTV16 O3-R6-R3 adaptive feasibility-preserving stabilization "
        "design-freeze structural self-test: PASS"
    )

def main(project_root: Path, drive_root: Path) -> int:
    root = Path(project_root).resolve()
    drive = Path(drive_root).resolve()
    out = drive / OUT
    blocked = drive / BLOCK
    gates: dict[str, dict[str, Any]] = {}
    stage = "preflight"

    def gate(name: str, condition: bool, detail: Any = None) -> None:
        gates[name] = {
            "status": "PASS" if condition else "FAIL",
            "detail": detail,
        }
        if not condition:
            raise GateError(f"{name}: {detail!r}")
        print(
            f"[PASS] {name}"
            + (f" -- {detail}" if detail is not None else "")
        )

    print("=" * 200)
    print(
        MILESTONE
        + " -- ADAPTIVE FEASIBILITY-PRESERVING STABILIZATION SEMANTICS DESIGN FREEZE"
    )
    print("=" * 200)
    print("DESIGN/FREEZE ONLY. NO STABILIZED NONLINEAR EXECUTION.")
    print("NO STATE MUTATION. NO SUPPORT EXPANSION. NO DAMPING EXECUTION. NO TIME ADVANCE.")
    print("INTERMEDIATE RELAXED SATURATION IS A COMPUTATIONAL PRESSURE-DRIVING ITERATE, NOT A CERTIFIED PHYSICAL STATE.")
    print("FINAL CONVERGENCE MUST RECOVER THE ORIGINAL UNDAMPED FIXED POINT AND CLOSURE.")
    print()

    try:
        stage = "repository_authority"
        parent = git_text(root, "rev-parse", "HEAD^")
        dirty = git_text(root, "status", "--porcelain")
        gate("repository_parent_is_R2R2_commit", parent == PARENT_COMMIT, parent)
        gate("repository_clean", dirty == "", repr(dirty))

        r2r2_path = root / R2R2_RUNNER
        gate("R2R2_runner_present", r2r2_path.is_file(), str(r2r2_path))
        r2r2_actual_blob = git_text(root, "hash-object", str(r2r2_path))
        gate(
            "R2R2_runner_blob_exact",
            r2r2_actual_blob == R2R2_BLOB,
            r2r2_actual_blob,
        )

        stage = "R2R2_result_binding"
        r2d = drive / R2R2_OUT
        gate("R2R2_output_directory_present", r2d.is_dir(), str(r2d))
        manifest = verify_manifest(r2d, R2R2_MANIFEST)
        gate("R2R2_manifest_payload_count_exact_7", len(manifest) == 7, len(manifest))
        gate(
            "R2R2_manifest_payload_set_exact",
            set(manifest) == EXPECTED_R2R2_PAYLOADS,
            sorted(manifest),
        )

        summary = load_json(r2d / R2R2_SUMMARY)
        design = load_json(r2d / R2R2_DESIGN)
        decision = load_json(r2d / R2R2_DECISION)

        gate(
            "R2R2_PASS_status_bound",
            summary.get("status", "").startswith(
                "AV4F4R3R3R3R3R3O3R6R2R2_"
            )
            and summary.get("physical_time_advanced") is False
            and summary.get("damping_executed") is False
            and summary.get("coupled_continuation_executed") is False
            and summary.get("support_domain_changed") is False,
            summary.get("status"),
        )
        gate(
            "R2R2_boundary_exact",
            int(summary.get("evaluated_point_count", -1)) == 23
            and int(summary.get("new_point_checkpoint_count", -1)) == 23
            and int(summary.get("reused_point_checkpoint_count", -1)) == 0
            and summary.get("coarse_nonmonotonic_feasibility_observed") is False
            and int(summary.get("coarse_transition_count", -1)) == 1
            and int(summary.get("first_boundary_feasible_index", -1))
                == FIRST_FEASIBLE_INDEX
            and int(summary.get("first_boundary_infeasible_index", -1))
                == FIRST_INFEASIBLE_INDEX
            and abs(
                float(summary.get("first_boundary_feasible_omega", -1.0))
                - FIRST_FEASIBLE_OMEGA
            ) <= 1.0e-15
            and abs(
                float(summary.get("first_boundary_infeasible_omega", -1.0))
                - FIRST_INFEASIBLE_OMEGA
            ) <= 1.0e-15
            and abs(
                float(
                    summary.get(
                        "first_boundary_infeasible_minimum_unserved_mass_kg",
                        -1.0,
                    )
                )
                - FIRST_INFEASIBLE_UNSERVED_KG
            ) <= 1.0e-12
            and int(summary.get("P2_controlling_CV_id", -1))
                == P2_CONTROLLING_CV
            and abs(
                float(summary.get("P2_minimum_unserved_mass_kg", -1.0))
                - P2_UNSERVED_KG
            ) <= 1.0e-10,
            {
                "feasible_omega": summary.get("first_boundary_feasible_omega"),
                "infeasible_omega": summary.get("first_boundary_infeasible_omega"),
                "upper_unserved_kg": summary.get(
                    "first_boundary_infeasible_minimum_unserved_mass_kg"
                ),
            },
        )
        gate(
            "R2R2_design_freeze_only_authority_exact",
            design.get("O3R6R3_design_freeze_authorized") is True
            and design.get("O3R6R3_execution_authorized") is False
            and design.get("fixed_global_damping_factor_authorized") is False
            and design.get("adaptive_stabilization_execution_authorized")
                is False
            and design.get("support_expansion_authorized") is False
            and decision.get("O3R6R3_design_freeze_authorized") is True
            and decision.get("O3R6R3_execution_authorized") is False
            and decision.get("O3R7_authorized") is False,
        )

        stage = "R2R2_point_checkpoint_binding"
        points_root = drive / R2R2_POINTS
        gate("R2R2_point_checkpoint_root_present", points_root.is_dir(), str(points_root))
        manifest_paths = sorted(points_root.glob("omega_*_of_1024/*_Manifest.csv"))
        gate("R2R2_point_checkpoint_count_exact_23", len(manifest_paths) == 23, len(manifest_paths))

        verified_indices: list[int] = []
        for mp in manifest_paths:
            dirname = mp.parent.name
            try:
                idx = int(dirname.split("_")[1])
            except Exception as exc:
                raise GateError(f"bad_point_checkpoint_dir:{dirname}:{exc!r}")
            state_name, result_name, manifest_name = point_names(idx)
            m = verify_manifest(mp.parent, manifest_name)
            gate(
                f"R2R2_point_{idx:04d}_manifest_exact",
                set(m) == {state_name, result_name},
            )
            verified_indices.append(idx)

        gate(
            "R2R2_first_boundary_point_checkpoints_present",
            FIRST_FEASIBLE_INDEX in verified_indices
            and FIRST_INFEASIBLE_INDEX in verified_indices,
            verified_indices,
        )

        fdir = point_dir(points_root, FIRST_FEASIBLE_INDEX)
        idir = point_dir(points_root, FIRST_INFEASIBLE_INDEX)
        _, fres_name, _ = point_names(FIRST_FEASIBLE_INDEX)
        _, ires_name, _ = point_names(FIRST_INFEASIBLE_INDEX)
        fres = load_json(fdir / fres_name)
        ires = load_json(idir / ires_name)
        gate(
            "R2R2_first_boundary_orientation_recertified",
            fres.get("exact_frozen_E2_feasible") is True
            and ires.get("exact_frozen_E2_feasible") is False
            and abs(float(fres.get("omega")) - FIRST_FEASIBLE_OMEGA)
                <= 1.0e-15
            and abs(float(ires.get("omega")) - FIRST_INFEASIBLE_OMEGA)
                <= 1.0e-15
            and abs(
                float(ires.get("minimum_unserved_mass_kg"))
                - FIRST_INFEASIBLE_UNSERVED_KG
            ) <= 1.0e-12,
        )

        stage = "stabilization_semantics_freeze"

        operator_semantics = {
            "operator_id":
                "PAD_STREAM_ADAPTIVE_FEASIBILITY_PRESERVING_FIXED_POINT_V1",
            "purpose": (
                "Keep each numerical saturation iterate inside the domain on "
                "which the exact frozen-E2 five-stage assignment map is defined, "
                "without changing support, conservation constraints, EOS, pressure "
                "physics, lexicographic objectives, or final fixed-point criteria."
            ),
            "state_roles": {
                "S_iter_k": (
                    "Computational pressure-driving saturation iterate. It may be "
                    "under-relaxed and is NOT by itself a certified physical state."
                ),
                "P_map_k": (
                    "Exact finite-volume pressure solution generated from S_iter_k."
                ),
                "x_map_k": (
                    "Exact five-stage frozen-E2 lexicographic assignment evaluated "
                    "under P_map_k."
                ),
                "m_map_k": (
                    "Exact Cartesian event mass from immutable residual sidecar plus "
                    "mapped x_map_k."
                ),
                "S_map_k": (
                    "Exact EOS inversion of m_map_k under P_map_k. This is the "
                    "scientifically certified physical map candidate F(S_iter_k)."
                ),
            },
            "exact_map_evaluation": [
                "Solve pressure exactly from S_iter_k.",
                "Require pressure linear relative residual < 1e-8.",
                "Require immutable residual sidecar capacity feasibility.",
                "Run the unchanged exact five-stage frozen-E2 lexicographic assignment.",
                "Require exact per-CV mass and cell-capacity constraints.",
                "Construct m_map_k = residual + mapped assignment.",
                "Invert EOS exactly to S_map_k and certify saturation/mass closure.",
                "Durably checkpoint the physical map candidate before any line search.",
            ],
            "lookahead_domain_test": (
                "For a trial next numerical iterate S_trial, solve its exact pressure "
                "field and run the exact frozen-E2 minimum-unserved LP. A trial is "
                "domain-feasible only if minimum unserved <= 1e-6 kg, CV equality "
                "Linf <= 1e-6 kg, maximum capacity excess <= 1e-6 kg, and the "
                "immutable residual sidecar is capacity-feasible."
            ),
            "full_step_rule": (
                "First test omega=1, i.e. S_trial=S_map_k. If it is domain-feasible, "
                "accept the full numerical step."
            ),
            "adaptive_backtracking_rule": (
                "If omega=1 is infeasible, test omega=1/2, 1/4, 1/8, ... until a "
                "positive feasible point is found or omega=1/1024 is reached."
            ),
            "binary_refinement_rule": (
                "Once a feasible lower omega and infeasible upper omega are known, "
                "binary-refine their interval on the denominator-1024 dyadic grid "
                "until the bracket width is 1/1024. Accept the largest certified "
                "feasible lower endpoint."
            ),
            "sampled_monotonicity_guard": (
                "If evaluated line-search points exhibit infeasible->feasible reversal "
                "in their ordered omega sequence after the first feasible->infeasible "
                "transition, stop as a scientific/design failure; do not force a "
                "monotone interpretation."
            ),
            "minimum_positive_step_rule": (
                "If omega=1/1024 is not domain-feasible, stop with scientific failure. "
                "No smaller automatic step, support expansion, tolerance relaxation, "
                "clipping, or global rescaling is authorized."
            ),
            "accepted_iterate_update": (
                "S_iter_(k+1) = S_iter_k + omega_k*(S_map_k - S_iter_k). "
                "This under-relaxed field is a computational iterate only."
            ),
            "first_stabilized_restart": {
                "source": "O3-R6-R2-R2 certified first-boundary checkpoint",
                "omega_index": FIRST_FEASIBLE_INDEX,
                "omega_denominator": BOUNDARY_DEN,
                "omega": FIRST_FEASIBLE_OMEGA,
                "rule": (
                    "The controlled stabilized execution may reuse the exact "
                    "omega=147/1024 R2-R2 diagnostic saturation/pressure checkpoint "
                    "after manifest and pressure/capacity recertification; it must not "
                    "recompute the 23-point R2-R2 scan merely to recreate that point."
                ),
            },
            "max_nonlinear_iterations": MAX_NONLINEAR_ITERATIONS,
            "fixed_global_damping_factor": None,
            "support_domain": "unchanged frozen E2/H2",
            "lexicographic_objectives": "unchanged O2 five-stage order",
            "physical_time_advance_within_iterations": False,
        }

        convergence_semantics = {
            "convergence_id":
                "PAD_STREAM_ORIGINAL_UNDAMPED_FIXED_POINT_CLOSURE_V1",
            "false_convergence_prohibited": [
                "Small accepted damped step is not convergence.",
                "Small omega is not convergence.",
                "Line-search bracket width is not convergence.",
                "A computational S_iter checkpoint is not a physical fixed point.",
            ],
            "required_simultaneously": {
                "omega_k_exactly_full_step": 1.0,
                "raw_fixed_point_saturation_Linf_max":
                    SATURATION_FIXED_POINT_LINF_TOL,
                "pressure_relative_L2_change_max": PRESSURE_REL_L2_TOL,
                "grid_mass_Linf": "A2-E/O3-R5 mass tolerance",
                "per_CV_mass": "exact within frozen execution tolerance",
                "cell_capacity": "satisfied",
                "global_mass_relative_error_max": GLOBAL_MASS_REL_TOL,
                "pressure_linear_relative_residual_max":
                    PRESSURE_LINEAR_REL_RESIDUAL_MAX,
            },
            "raw_fixed_point_residual_definition": (
                "max_abs(S_map_k - S_iter_k), never the smaller accepted "
                "max_abs(S_iter_(k+1)-S_iter_k)."
            ),
            "final_closure": [
                "Freeze the converged five-stage assignment.",
                "Solve one final exact pressure system from the converged saturation.",
                "Require final pressure change <= 1e-10 relative L2.",
                "Recompute capacity under final pressure.",
                "Require frozen grid mass remains capacity-feasible.",
                "Invert the same frozen mass under final pressure.",
                "Require final saturation change <= 1e-10 Linf.",
                "Require original CV/global mass closure.",
                "Otherwise scientific FAIL; no automatic damping/support change/rerun.",
            ],
        }

        checkpoint_semantics = {
            "policy_id":
                "PAD_STREAM_DURABLE_CHECKPOINT_POLICY_V2_STABILIZED_SOLVER",
            "inherits": "PAD_STREAM_DURABLE_CHECKPOINT_POLICY_V1",
            "physical_map_candidate_checkpoint": (
                "After every expensive exact five-stage map evaluation passes mass, "
                "capacity, EOS, and saturation checks, write an immutable PHYSICAL_MAP_"
                "CANDIDATE checkpoint before line search."
            ),
            "accepted_computational_iterate_checkpoint": (
                "After omega_k is selected, write S_iter_(k+1), the full line-search "
                "audit, and restart metadata as COMPUTATIONAL_ITERATE_ACCEPTED. This "
                "checkpoint is not physical-state authority."
            ),
            "line_search_point_checkpoint": (
                "Each completed omega feasibility test is individually immutable and "
                "reusable after manifest/SHA and pressure/capacity recertification."
            ),
            "lex_stage_checkpointing": {
                "required_after_each_completed_stage": [1, 2, 3, 4, 5],
                "classification": "COMPUTATIONAL_RESUME_ONLY",
                "contents": [
                    "nonlinear iteration",
                    "stage number/name",
                    "stage objective value",
                    "all prior lexicographic freeze values",
                    "current primal assignment required for certification",
                    "HiGHS row basis statuses",
                    "HiGHS column basis statuses",
                    "model dimensions and exact graph identity",
                    "manifest/SHA identities",
                ],
                "restart_rule": (
                    "Rebuild the exact same frozen-E2 component model, recreate all "
                    "completed lexicographic freeze constraints, restore the validated "
                    "HiGHS basis, recertify completed stage objective values, then "
                    "continue at the next unfinished stage."
                ),
                "basis_round_trip_gate": (
                    "The controlled execution must self-test getBasis/setBasis "
                    "round-trip equivalence under highspy 1.15.1 before relying on "
                    "basis restart. If the basis round-trip gate fails, execution "
                    "BLOCKS before an expensive solve; it may not silently pretend "
                    "stage-resume is available."
                ),
            },
            "final_fixed_point_checkpoint": (
                "Only after undamped convergence and final closure write "
                "CERTIFIED_NONLINEAR_FIXED_POINT_STATE."
            ),
            "physical_time_advance": False,
        }

        failure_semantics = {
            "scientific_fail_conditions": [
                "No positive feasible omega >= 1/1024.",
                "Sampled nonmonotonic feasibility invalidates the bracket semantics.",
                "Any exact five-stage assignment infeasibility at a certified trial.",
                "Residual-sidecar capacity infeasibility.",
                "EOS/saturation/mass/capacity certification failure.",
                "No undamped fixed-point convergence within 100 nonlinear iterations.",
                "Final closure failure.",
            ],
            "technical_block_conditions": [
                "Authority/blob/manifest mismatch.",
                "Checkpoint corruption or namespace conflict.",
                "HiGHS 1.15.1 basis round-trip restart self-test failure before solve.",
                "Unable to recreate a completed lexicographic stage exactly on restart.",
            ],
            "forbidden_automatic_repairs": [
                "support expansion beyond frozen E2/H2",
                "capacity relaxation",
                "per-CV mass relaxation",
                "mass clipping/discarding",
                "global rescaling",
                "changing O2 lexicographic objective order",
                "fixed arbitrary global damping factor",
                "omega below 1/1024",
                "automatic second event refresh",
                "physical-time advance during stabilization",
            ],
        }

        summary_out = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "design_only": True,
            "R2R2_boundary_bound": True,
            "R2R2_first_feasible_omega": FIRST_FEASIBLE_OMEGA,
            "R2R2_first_infeasible_omega": FIRST_INFEASIBLE_OMEGA,
            "R2R2_boundary_width": 1.0 / BOUNDARY_DEN,
            "R2R2_P2_controlling_CV_id": P2_CONTROLLING_CV,
            "stabilization_operator_frozen": True,
            "adaptive_line_search_frozen": True,
            "fixed_global_damping_factor": None,
            "original_undamped_convergence_preserved": True,
            "support_domain_changed": False,
            "pressure_solve_executed": False,
            "assignment_executed": False,
            "damping_executed": False,
            "coupled_continuation_executed": False,
            "Darcy_Pollock_TOF_executed": False,
            "physical_time_advanced": False,
        }

        decision_out = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "next_milestone": (
                "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R6-R4 — "
                "controlled adaptive feasibility-preserving stabilized coupled execution"
            ),
            "O3R6R4_controlled_execution_authorized": True,
            "O3R6R4_must_use_frozen_R3_semantics": True,
            "fixed_global_damping_authorized": False,
            "support_expansion_authorized": False,
            "capacity_relaxation_authorized": False,
            "per_CV_mass_relaxation_authorized": False,
            "automatic_rerun_authorized": False,
            "O3R7_authorized": False,
            "R3R3R4_authorized": False,
            "F5_dataset_generation_authorized": False,
            "training_authorized": False,
        }

        files = {
            "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R3_Summary.json":
                json_bytes(summary_out),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R3_Adaptive_Stabilization_Operator_Contract.json":
                json_bytes(operator_semantics),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R3_Undamped_Convergence_and_Final_Closure_Contract.json":
                json_bytes(convergence_semantics),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R3_Stabilized_Checkpoint_Restart_Policy.json":
                json_bytes(checkpoint_semantics),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R3_Failure_Semantics.json":
                json_bytes(failure_semantics),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R3_Decision_Contract.json":
                json_bytes(decision_out),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R3_Final_Gate_Matrix.csv":
                csv_bytes([{"gate": k, **v} for k, v in gates.items()]),
        }
        immutable_publish(out, files)

        manifest_name = (
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R3_Artifact_Manifest.csv"
        )
        rows = [
            {
                "file": p.name,
                "sha256": sha256_file(p),
                "bytes": p.stat().st_size,
            }
            for p in sorted(out.iterdir())
            if p.is_file() and p.name != manifest_name
        ]
        immutable_publish(out, {manifest_name: csv_bytes(rows)})

        print()
        print("=" * 200)
        print(MILESTONE + ": DESIGN FREEZE PASS")
        print("=" * 200)
        print("R2-R2 feasible boundary        :", FIRST_FEASIBLE_OMEGA)
        print("R2-R2 infeasible boundary      :", FIRST_INFEASIBLE_OMEGA)
        print("Adaptive line search           : FROZEN")
        print("Fixed global damping           : NOT AUTHORIZED")
        print("Intermediate relaxed iterate   : COMPUTATIONAL ONLY")
        print("Undamped final convergence     : REQUIRED")
        print("Lex stage checkpointing        : REQUIRED")
        print("O3-R6-R4 controlled execution  : AUTHORIZED")
        print("O3-R7                          : NOT AUTHORIZED")
        print("Physical-time advance          : False")
        print("=" * 200)
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": MILESTONE,
            "status": STATUS_BLOCK,
            "failed_stage": stage,
            "exception": repr(exc),
            "gates": gates,
            "design_only": True,
            "stabilized_execution_executed": False,
            "damping_executed": False,
            "support_domain_changed": False,
            "physical_time_advanced": False,
            "O3R6R4_controlled_execution_authorized": False,
            "O3R7_authorized": False,
            "R3R3R4_authorized": False,
        }
        p = blocked / (
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R6R3_Blocked_Report.json"
        )
        if not p.exists():
            p.write_bytes(json_bytes(report))
        print(MILESTONE + ": TECHNICAL / AUTHORITY BLOCK")
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
    args = parse_args()
    if args.self_test:
        self_test()
        raise SystemExit(0)
    raise SystemExit(main(args.project_root, args.drive_root))
