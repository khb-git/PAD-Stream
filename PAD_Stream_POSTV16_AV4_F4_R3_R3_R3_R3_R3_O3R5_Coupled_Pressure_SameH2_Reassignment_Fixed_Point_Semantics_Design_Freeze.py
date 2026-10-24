#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

MILESTONE = "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R5"
STATUS_PASS = (
    "AV4F4R3R3R3R3R3O3R5_COUPLED_PRESSURE_SAME_H2_REASSIGNMENT_"
    "FIXED_POINT_SEMANTICS_DESIGN_FREEZE_PASS_NO_EXECUTION_NO_STATE_MUTATION_NO_TIME_ADVANCE"
)
STATUS_BLOCKED = "AV4F4R3R3R3R3R3O3R5_TECHNICAL_OR_AUTHORITY_BLOCK"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
EVENT_DAY = 413.78677770818403

PARENT_O3R4_COMMIT = "5c7e052b54aee4e3756e992be8c7ae3f736b1690"

O3R4_RUNNER = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R4_"
    "Exact_Frozen_E2_First_Refresh_Capacity_Feasibility_Audit.py"
)
O3R4_RUNNER_BLOB = "4446ca612d1f6a00472327818aff674d568f9ede"

O2_RUNNER = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O2_"
    "Persistent_Native_HiGHS_H2_Assignment_Execution.py"
)
O2_RUNNER_BLOB = "2e04f77750add23f9cfe5143119668450201354f"

A2E_RUNNER = (
    "PAD_Stream_POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution.py"
)
A2E_RUNNER_BLOB = "79a8969233b72b4543edd382a0c3d1028c6dca09"

BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"
O3R4_REL = (
    BASE_AV4
    / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R4_"
      "Exact_Frozen_E2_First_Refresh_Capacity_Feasibility_Audit"
)
O3R4_SUMMARY = "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R4_Summary.json"
O3R4_AUDIT = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R4_Exact_Feasibility_Audit.json"
O3R4_UNSERVED = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R4_Unserved_CV_Diagnostics.csv"
O3R4_DESIGN = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R4_Prospective_Coupling_Design.json"
O3R4_GATES = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R4_Final_Gate_Matrix.csv"
O3R4_MANIFEST = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R4_Artifact_Manifest.csv"
EXPECTED_O3R4_FILES = {
    O3R4_SUMMARY, O3R4_AUDIT, O3R4_UNSERVED, O3R4_DESIGN, O3R4_GATES
}
O3R4_STATUS = (
    "AV4F4R3R3R3R3R3O3R4_EXACT_FROZEN_E2_FIRST_REFRESH_CAPACITY_"
    "FEASIBILITY_AUDIT_PASS_NO_STATE_MUTATION_NO_FLOW_REFRESH_NO_TIME_ADVANCE"
)

OUT_REL = (
    BASE_AV4
    / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R5_"
      "Coupled_Pressure_SameH2_Fixed_Point_Semantics_Design_Freeze"
)
BLOCK_REL = BASE_AV4 / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R5_BLOCKED"

MAX_FIXED_POINT_ITERATIONS = 100
PRESSURE_REL_L2_TOL = 1.0e-10
SATURATION_LINF_TOL = 1.0e-10
PRESSURE_LINEAR_REL_RESIDUAL_MAX = 1.0e-8
GLOBAL_MASS_REL_TOL = 1.0e-10

class GateError(RuntimeError):
    pass

def git_text(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True, text=True, capture_output=True
    ).stdout.strip()

def git_blob(path: Path, root: Path) -> str:
    return git_text(root, "hash-object", str(path))

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def json_bytes(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True) + "\n").encode("utf-8")

def csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        return b""
    import io
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()), lineterminator="\n")
    w.writeheader()
    for row in rows:
        w.writerow(row)
    return buf.getvalue().encode("utf-8")

def immutable_publish(out: Path, files: dict[str, bytes]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        p = out / name
        if p.exists():
            if p.read_bytes() != data:
                raise GateError("immutable_publish_conflict:" + str(p))
        else:
            p.write_bytes(data)

def verify_manifest(directory: Path, manifest_name: str) -> dict[str, str]:
    p = directory / manifest_name
    if not p.is_file():
        raise GateError("manifest_missing:" + str(p))
    rows = list(csv.DictReader(p.read_text(encoding="utf-8").splitlines()))
    result: dict[str, str] = {}
    for row in rows:
        fn = row["file"]
        fp = directory / fn
        if not fp.is_file():
            raise GateError("manifest_payload_missing:" + fn)
        actual = sha256_file(fp)
        if actual != row["sha256"]:
            raise GateError("manifest_sha_mismatch:" + fn)
        result[fn] = actual
    return result

def self_test() -> None:
    assert MILESTONE.endswith("O3-R5")
    assert len(PARENT_O3R4_COMMIT) == 40
    assert MAX_FIXED_POINT_ITERATIONS == 100
    assert PRESSURE_REL_L2_TOL == 1.0e-10
    assert SATURATION_LINF_TOL == 1.0e-10
    print(
        "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R5 "
        "coupled pressure/same-H2 fixed-point semantics design-freeze self-test: PASS"
    )

def main(project_root: Path, drive_root: Path) -> int:
    root = Path(project_root).resolve()
    drive = Path(drive_root).resolve()
    out = drive / OUT_REL
    blocked = drive / BLOCK_REL
    gates: dict[str, dict[str, Any]] = {}
    stage = "preflight"

    def gate(name: str, cond: bool, detail: Any = None) -> None:
        gates[name] = {"status": "PASS" if cond else "FAIL", "detail": detail}
        if not cond:
            raise GateError(f"{name}: {detail!r}")
        print(f"[PASS] {name}" + (f" -- {detail}" if detail is not None else ""))

    print("=" * 196)
    print(
        "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R5 -- "
        "COUPLED PRESSURE / SAME-H2 REASSIGNMENT FIXED-POINT SEMANTICS DESIGN FREEZE"
    )
    print("=" * 196)
    print("DESIGN/FREEZE ONLY. NO HIGHS SOLVE. NO PRESSURE SOLVE. NO REASSIGNMENT EXECUTION.")
    print("NO DARCY/POLLOCK/TOF REGENERATION. NO REPROJECTION. NO PHYSICAL-TIME ADVANCE.")
    print("FROZEN E2/H2 SUPPORT, EXACT PER-CV MASS, IMMUTABLE RESIDUAL SIDECAR, AND O2 LEXICOGRAPHIC PRIORITIES ARE PRESERVED.")
    print()

    try:
        stage = "repository_authority"
        parent = git_text(root, "rev-parse", "HEAD^")
        status = git_text(root, "status", "--porcelain")
        gate("repository_parent_is_O3R4_commit", parent == PARENT_O3R4_COMMIT, parent)
        gate("repository_clean", status == "", repr(status))

        authorities = {
            O3R4_RUNNER: O3R4_RUNNER_BLOB,
            O2_RUNNER: O2_RUNNER_BLOB,
            A2E_RUNNER: A2E_RUNNER_BLOB,
        }
        for fn, expected in authorities.items():
            p = root / fn
            actual = git_blob(p, root) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact", actual == expected, actual)

        stage = "O3R4_result_binding"
        r4d = drive / O3R4_REL
        gate("O3R4_output_present", r4d.is_dir(), str(r4d))
        manifest = verify_manifest(r4d, O3R4_MANIFEST)
        gate("O3R4_manifest_exact_5", len(manifest) == 5, len(manifest))
        gate(
            "O3R4_manifest_payload_file_set_exact",
            set(manifest) == EXPECTED_O3R4_FILES,
            sorted(manifest),
        )
        s4 = load_json(r4d / O3R4_SUMMARY)
        d4 = load_json(r4d / O3R4_DESIGN)

        gate(
            "O3R4_exact_first_refresh_feasibility_certificate_bound",
            s4.get("status") == O3R4_STATUS
            and abs(float(s4.get("event_day", float("nan"))) - EVENT_DAY) <= 1e-12
            and s4.get("exact_frozen_E2_first_refresh_capacity_feasible") is True
            and float(s4.get("minimum_unserved_mass_kg", float("nan"))) == 0.0
            and int(s4.get("unserved_CV_count_above_1e-6_kg", -1)) == 0
            and float(s4.get("CV_equality_Linf_kg", 1.0)) <= 1.0e-6
            and float(s4.get("maximum_cell_capacity_excess_kg", 1.0)) <= 1.0e-6
            and s4.get("deployment_assignment_executed") is False
            and s4.get("flow_refresh_executed") is False
            and s4.get("reprojection_executed") is False
            and s4.get("support_domain_changed") is False
            and s4.get("physical_time_advanced") is False,
            {
                "minimum_unserved_mass_kg": s4.get("minimum_unserved_mass_kg"),
                "CV_equality_Linf_kg": s4.get("CV_equality_Linf_kg"),
                "maximum_cell_capacity_excess_kg": s4.get("maximum_cell_capacity_excess_kg"),
            },
        )
        gate(
            "O3R4_authorizes_O3R5_design_only",
            d4.get("O3R5_design_only_authorized") is True
            and d4.get("O3R5_execution_authorized") is False
            and d4.get("R3R3R4_authorized") is False
            and d4.get("support_expansion_authorized") is False
            and d4.get("second_event_refresh_authorized") is False
            and d4.get("F5_dataset_generation_authorized") is False
            and d4.get("training_authorized") is False,
        )

        stage = "semantics_freeze"

        state_definition = {
            "event_day": EVENT_DAY,
            "frozen_quantities": {
                "per_CV_event_component_mass": "O2 event_CV_component_mass_kg; exact equality at every nonlinear iterate",
                "residual_sidecar_grid_mass": "O2 frozen_residual_grid_component_mass_kg; immutable at every nonlinear iterate",
                "support_graph": "O2 frozen E2/H2 horizontal radius-2 graph only",
                "pore_volume_and_rock": "A2-E / O2 frozen grid PV, permeability, porosity and spatial Corey fields",
                "reference_gas_pressure": "O2/A2-E reference gas pressure",
                "event_time": EVENT_DAY,
            },
            "iterated_quantities": {
                "E2_assignment_mass_x": "nonnegative edge mass satisfying exact per-CV demand and current-pressure cell capacity",
                "cartesian_event_mass_m": "residual sidecar + E2 mapped assignment",
                "saturation_S": "EOS inversion of m under current same-time pressure",
                "pressure_P": "finite-volume pressure solution under mobility(S)",
                "cell_capacity_C": "maximum local CO2 component mass at Sg=0.60 under P",
            },
        }

        assignment_semantics = {
            "graph": "frozen O2 E2 graph; no new edges",
            "constraints": [
                "x_e >= 0 on frozen E2 edges only",
                "for every CV c: sum_{e incident to c} x_e = frozen event CV mass M_c",
                "for every Cartesian cell j: sum_{e terminating in j} x_e <= C_j(P) - residual_j",
                "residual_j is immutable and must itself remain within C_j(P)",
            ],
            "lexicographic_objectives_preserved_from_O2": [
                "Stage 1: minimize H2 second-shell mass",
                "Stage 2: minimize total extension mass E2\\E0",
                "Stage 3: minimize parent-ownership L1 deviation on E0",
                "Stage 4: minimize raw-event-EOS L1 deviation on E0",
                "Stage 5: deterministic global E2 pair-rank tiebreak",
            ],
            "objective_policy": (
                "Objective definitions and order are frozen from O2. Numeric optimum values are recomputed "
                "at each pressure iterate because the admissible cell-capacity vector changes with pressure."
            ),
            "computationally_allowed_without_scientific_change": [
                "exact-zero demand/capacity pruning only",
                "exact disconnected-component decomposition",
                "persistent native HiGHS",
                "basis reuse across lexicographic stages and nonlinear iterations when accepted by solver",
            ],
            "prohibited": [
                "tolerance-based support pruning",
                "capacity relaxation",
                "per-CV mass relaxation",
                "mass clipping or discarding",
                "global mass rescaling",
                "support radius >2",
                "vertical support",
                "H2+V1 fallback",
            ],
        }

        iteration_semantics = {
            "initial_state_k0": {
                "x_0": "exact O2 optimized E2 event assignment",
                "m_0": "exact O2 event_grid_component_mass_kg",
                "P_0": "O2/A2-E parent refreshed pressure",
                "S_0": "exact EOS inversion of m_0 under P_0, already certified by O3-R2",
            },
            "iteration_k_to_kplus1": [
                "1. Compute spatial mobility from S_k using frozen spatial Corey fields.",
                "2. Assemble and solve one finite-volume pressure system to obtain candidate P_{k+1}.",
                "3. Require pressure linear relative residual < 1e-8.",
                "4. Compute local component-mass capacity C(P_{k+1}) at Sg=0.60.",
                "5. Require immutable residual sidecar <= C(P_{k+1}) cellwise; otherwise SCIENTIFIC FAIL.",
                "6. On the same frozen E2 graph, solve the exact O2 five-stage lexicographic reassignment under C(P_{k+1}) - residual.",
                "7. Reconstruct m_{k+1} = residual + mapped(x_{k+1}); require exact per-CV and global mass closure.",
                "8. EOS-invert m_{k+1} under P_{k+1} to obtain S_{k+1}; require saturation in [0.20, 0.80].",
                "9. Evaluate convergence against (P_k, S_k, m_k). If not converged, accept the full update with no damping and continue.",
            ],
            "single_refresh_semantics": (
                "All k-iterations are internal nonlinear iterations of ONE same-time event flow refresh at the frozen event day. "
                "They are not separate event refreshes. No Darcy/Pollock/TOF regeneration occurs inside the loop."
            ),
            "under_relaxation": "not authorized in first controlled execution",
            "maximum_iterations": MAX_FIXED_POINT_ITERATIONS,
        }

        convergence_semantics = {
            "pressure_relative_L2_tolerance": PRESSURE_REL_L2_TOL,
            "saturation_Linf_tolerance": SATURATION_LINF_TOL,
            "pressure_linear_relative_residual_max": PRESSURE_LINEAR_REL_RESIDUAL_MAX,
            "global_mass_relative_tolerance": GLOBAL_MASS_REL_TOL,
            "grid_mass_convergence_tolerance": (
                "max(1e-8 kg, 1e-10 * max(abs(m_{k+1}))) using the A2-E cell-mass tolerance form"
            ),
            "all_required_simultaneously": [
                "relative_L2(P_{k+1}, P_k) <= 1e-10",
                "Linf(S_{k+1} - S_k) <= 1e-10",
                "Linf(m_{k+1} - m_k) <= grid-mass convergence tolerance",
                "per-CV assignment mass equality certified",
                "cell capacities certified",
                "global component-mass closure <= 1e-10 relative",
            ],
            "final_closure_recertification": [
                "After provisional convergence, rebuild mobility/transmissibilities from S_*.",
                "Solve one closure pressure system without changing assignment.",
                "Require closure pressure relative L2 versus P_* <= 1e-10.",
                "Recompute capacity and require frozen residual + mapped assignment within capacity.",
                "EOS-reconstruct mass and require cellwise/global mass closure.",
            ],
        }

        execution_boundary = {
            "O3R6_authorized_scope": [
                "execute the coupled pressure / same-H2 assignment fixed-point exactly as frozen here",
                "publish iteration telemetry",
                "publish converged or formally failed pressure, saturation, grid mass and E2 assignment diagnostics",
                "if converged, publish a coupled same-time event-state checkpoint",
            ],
            "O3R6_explicitly_not_authorized": [
                "Darcy face-flux regeneration",
                "Pollock streamline regeneration",
                "TOF/weight regeneration",
                "refreshed-geometry bounded reprojection",
                "physical-time advance",
                "Day500 continuation",
                "support expansion",
                "second event refresh",
                "F5 dataset generation",
                "training",
                "CMG",
            ],
            "post_O3R6_if_PASS": (
                "Only after an O3-R6 coupled fixed-point PASS may a new O3-R7 design/execution milestone "
                "be considered for the single final Darcy/Pollock/TOF refresh and bounded reprojection."
            ),
        }

        failure_semantics = {
            "scientific_fail_conditions": [
                "immutable residual sidecar exceeds current-pressure capacity",
                "frozen E2 lexicographic assignment becomes infeasible under an iterate pressure",
                "pressure/saturation/grid-mass fixed point does not converge within 100 iterations",
                "final closure pressure fails the frozen convergence tolerance",
                "mass, saturation, or cell-capacity certification fails",
            ],
            "on_scientific_fail": [
                "stop immediately",
                "publish formal scientific-fail evidence",
                "do not alter support",
                "do not relax capacity or per-CV mass",
                "do not damp/under-relax automatically",
                "do not rerun automatically",
                "do not regenerate Darcy/Pollock/TOF",
                "do not advance physical time",
            ],
            "technical_block_conditions": [
                "repository/manifest/blob authority mismatch",
                "missing required artifact",
                "solver import/API failure",
                "unexpected exception before a scientific classification can be certified",
            ],
        }

        summary = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "event_day": EVENT_DAY,
            "O3R4_exact_first_refresh_feasibility_bound": True,
            "coupled_fixed_point_semantics_frozen": True,
            "O2_lexicographic_objectives_preserved": True,
            "frozen_E2_support_preserved": True,
            "per_CV_mass_preserved": True,
            "residual_sidecar_preserved": True,
            "maximum_fixed_point_iterations": MAX_FIXED_POINT_ITERATIONS,
            "pressure_relative_L2_tolerance": PRESSURE_REL_L2_TOL,
            "saturation_Linf_tolerance": SATURATION_LINF_TOL,
            "design_only": True,
            "assignment_executed": False,
            "pressure_solve_executed": False,
            "flow_refresh_completed": False,
            "Darcy_Pollock_TOF_regenerated": False,
            "reprojection_executed": False,
            "support_domain_changed": False,
            "physical_time_advanced": False,
        }

        handoff = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "next_milestone": (
                "POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R6 — "
                "controlled coupled pressure/same-H2 reassignment fixed-point execution"
            ),
            "O3R6_execution_authorized": True,
            "O3R6_required_parent_status": STATUS_PASS,
            "O3R6_scope": execution_boundary["O3R6_authorized_scope"],
            "O3R6_not_authorized": execution_boundary["O3R6_explicitly_not_authorized"],
            "O3R7_authorized": False,
            "R3R3R4_authorized": False,
            "F5_dataset_generation_authorized": False,
            "training_authorized": False,
        }

        decision = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "scientific_constraints_relaxed": False,
            "coupling_iteration_semantics_extended": True,
            "O2_lexicographic_objective_order_changed": False,
            "support_domain_changed": False,
            "capacity_relaxed": False,
            "per_CV_mass_relaxed": False,
            "mass_clipped_or_discarded": False,
            "global_rescaling_performed": False,
            "under_relaxation_authorized": False,
            "second_event_refresh_authorized": False,
            "physical_time_advance_authorized": False,
            "O3R6_execution_authorized": True,
            "O3R7_authorized": False,
            "R3R3R4_authorized": False,
            "F5_dataset_generation_authorized": False,
            "training_authorized": False,
        }

        files = {
            "PAD_Stream_POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R5_Summary.json":
                json_bytes(summary),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R5_Coupled_Fixed_Point_Semantics_Contract.json":
                json_bytes({
                    "milestone": MILESTONE,
                    "status": STATUS_PASS,
                    "state_definition": state_definition,
                    "assignment_semantics": assignment_semantics,
                    "iteration_semantics": iteration_semantics,
                }),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R5_Convergence_and_Failure_Contract.json":
                json_bytes({
                    "milestone": MILESTONE,
                    "status": STATUS_PASS,
                    "convergence_semantics": convergence_semantics,
                    "failure_semantics": failure_semantics,
                }),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R5_O3R6_Handoff_Contract.json":
                json_bytes(handoff),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R5_Decision_Contract.json":
                json_bytes(decision),
            "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R5_Final_Gate_Matrix.csv":
                csv_bytes([{"gate": k, **v} for k, v in gates.items()]),
        }
        immutable_publish(out, files)

        manifest_name = "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R5_Artifact_Manifest.csv"
        rows = []
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name != manifest_name:
                rows.append({
                    "file": p.name,
                    "sha256": sha256_file(p),
                    "bytes": p.stat().st_size,
                })
        immutable_publish(out, {manifest_name: csv_bytes(rows)})

        print()
        print("=" * 196)
        print("POSTV16-AV4-F4-R3-R3-R3-R3-R3-O3-R5: DESIGN FREEZE PASS")
        print("=" * 196)
        print("Event day                             :", EVENT_DAY)
        print("O3-R4 exact first-refresh feasible   : True")
        print("Frozen support                       : E2/H2 unchanged")
        print("Per-CV event mass                    : exact / unchanged")
        print("Residual sidecar                     : immutable")
        print("Assignment objective order           : O2 five-stage lexicographic unchanged")
        print("Max coupled iterations               :", MAX_FIXED_POINT_ITERATIONS)
        print("Pressure relative-L2 tolerance       :", PRESSURE_REL_L2_TOL)
        print("Saturation Linf tolerance            :", SATURATION_LINF_TOL)
        print("Under-relaxation                     : NOT AUTHORIZED")
        print("Darcy/Pollock/TOF / reprojection     : NOT EXECUTED")
        print("Physical-time advance                : False")
        print("O3-R6 coupled fixed-point execution  : AUTHORIZED")
        print("O3-R7 / R3-R3-R4 / F5 / training    : NOT AUTHORIZED")
        print("=" * 196)
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": MILESTONE,
            "status": STATUS_BLOCKED,
            "failed_stage": stage,
            "exception": repr(exc),
            "gates": gates,
            "design_published": False,
            "assignment_executed": False,
            "pressure_solve_executed": False,
            "flow_refresh_completed": False,
            "reprojection_executed": False,
            "support_domain_changed": False,
            "physical_time_advanced": False,
            "automatic_rerun_authorized": False,
            "O3R6_execution_authorized": False,
            "R3R3R4_authorized": False,
            "F5_dataset_generation_authorized": False,
            "training_authorized": False,
        }
        p = blocked / "POSTV16_AV4_F4_R3_R3_R3_R3_R3_O3R5_Blocked_Report.json"
        if not p.exists():
            p.write_bytes(json_bytes(report))
        print()
        print("=" * 196)
        print(MILESTONE + ": TECHNICAL / AUTHORITY BLOCK")
        print("Stage    :", stage)
        print("Exception:", repr(exc))
        print("NO EXECUTION AUTHORITY GRANTED.")
        print("=" * 196)
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
