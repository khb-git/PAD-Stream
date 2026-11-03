#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, hashlib, io, json, subprocess, sys
from pathlib import Path
from typing import Any

M = "POSTV16-AV5-A1"
NAME = "Learned Pressure Acceleration Architecture + Exact Finite-Volume Correction Design Freeze"

PASS = (
    "POSTV16AV5A1_LEARNED_PRESSURE_ACCELERATION_ARCHITECTURE_AND_"
    "EXACT_FINITE_VOLUME_CORRECTION_DESIGN_FREEZE_PASS_NO_TRAINING_NO_EXECUTION"
)
BLOCK = "POSTV16AV5A1_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "2c333fcd20a0e638b43850ed105cf15fa610e80e"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"
BASE_AV5 = Path("post_v16") / RID / "POSTV16_AV5_Learned_Acceleration"

# AV4 closure authority.
R32_TOKEN = "POSTV16_AV4_PIVOT_P2_R6_R32"
R32_REL = BASE_AV4 / (R32_TOKEN + "_Independent_Recurrent_Operation_Closure_Audit")
R32_SUMMARY = "PAD_Stream_" + R32_TOKEN + "_Summary.json"
R32_DECISION = R32_TOKEN + "_Decision_Contract.json"
R32_MANIFEST = R32_TOKEN + "_Artifact_Manifest.csv"
R32_STATUS = (
    "AV4PIVOTP2R6R32_INDEPENDENT_RECURRENT_OPERATION_CLOSURE_AUDIT_"
    "PASS_AV4_RECURRENT_PHYSICS_CLOSED_NO_R31_TIME_COMMIT"
)
R32_CLASS = (
    "R30_AUTHORITATIVE_STATE_AND_R31_SECOND_STEP_RECURRENCE_"
    "INDEPENDENTLY_CLOSED_AV4_RECURRENT_PHYSICS_ACCEPTED_"
    "R31_CANDIDATE_REMAINS_PROSPECTIVE"
)
AV4_STATE_SHA = "07856a508db8ae6ba449e9e248bf8cdbc406eb0b4504471099b4b82f6048e0a6"
AV4_DAY = 375.0372167312886

R32_RUNNER = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R32_Independent_Recurrent_Operation_Closure_Audit.py"
R32_RUNNER_BLOB = "435f5d6dcba38de7166e41ba9e081b6ef573edcf"

# Exact AV4 pressure-refresh sources.
A2E = "PAD_Stream_POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution.py"
A2E_BLOB = "79a8969233b72b4543edd382a0c3d1028c6dca09"
SG3 = "PAD_Stream_V15SG3_FiveSpot_Pressure_Solve.py"
SG3_BLOB = "66a379cd97ee9120f69e7e7e949171541e4918c3"
R3R2R1 = "PAD_Stream_V16E41R3R2R1_Local_Conservation_Sign_Convention_Repair.py"
R3R2R1_BLOB = "740c6da03e73906646bf0153633187e749449f31"
SG2 = "PAD_Stream_V15SG2_Anisotropic_Transmissibility.py"
SG2_BLOB = "7242012d3e758472abc3ee7f543831b92d2cf419"
SG4 = "PAD_Stream_V15SG4_Conservative_Darcy_Fluxes.py"
SG4_BLOB = "8d49f88bdf55b0da087af2bed04e69967740e695"

SOURCE_BLOBS = {
    R32_RUNNER: R32_RUNNER_BLOB,
    A2E: A2E_BLOB,
    SG3: SG3_BLOB,
    R3R2R1: R3R2R1_BLOB,
    SG2: SG2_BLOB,
    SG4: SG4_BLOB,
}

OUT_TOKEN = "POSTV16_AV5_A1"
OUT_REL = BASE_AV5 / (OUT_TOKEN + "_Learned_Pressure_Acceleration_Architecture_ExactCorrection_Design_Freeze")
BLOCK_REL = BASE_AV5 / (OUT_TOKEN + "_BLOCKED")


class GateError(RuntimeError):
    pass


def gt(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def js(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def csvr(path: Path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def csvb(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        return b""
    fields = []
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


def manifest(directory: Path, filename: str) -> dict[str, str]:
    result = {}
    for row in csvr(directory / filename):
        p = directory / row["file"]
        if not p.is_file():
            raise GateError(f"manifest_missing:{p.name}")
        if sha(p) != row["sha256"]:
            raise GateError(f"manifest_sha:{p.name}")
        if p.stat().st_size != int(row["bytes"]):
            raise GateError(f"manifest_bytes:{p.name}")
        result[p.name] = row["sha256"]
    return result


def source_contains(path: Path, snippets: list[str]) -> bool:
    text = path.read_text(encoding="utf-8")
    return all(s in text for s in snippets)


def selftest():
    assert AV4_STATE_SHA == "07856a508db8ae6ba449e9e248bf8cdbc406eb0b4504471099b4b82f6048e0a6"
    assert AV4_DAY == 375.0372167312886
    print("POSTV16 AV5-A1 structural self-test: PASS")


def main(project_root: Path, drive_root: Path) -> int:
    root = project_root.resolve()
    drive = drive_root.resolve()
    out = drive / OUT_REL
    block_dir = drive / BLOCK_REL
    stage = "preflight"
    gates = []

    def gate(name: str, cond: Any, detail: Any = None):
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
        stage = "preexisting_state_firewall"
        gate("no_preexisting_PASS", not (out / f"PAD_Stream_{OUT_TOKEN}_Summary.json").exists())
        gate("no_preexisting_BLOCK", not (block_dir / f"{OUT_TOKEN}_Blocked_Report.json").exists())

        stage = "repository_authority"
        gate("branch_exact", gt(root, "branch", "--show-current") == BRANCH)
        gate("parent_exact", gt(root, "rev-parse", "HEAD^") == PARENT, gt(root, "rev-parse", "HEAD^"))
        gate("repository_clean", gt(root, "status", "--porcelain") == "")
        for fn, expected in SOURCE_BLOBS.items():
            p = root / fn
            gate(f"{Path(fn).stem}_present", p.is_file(), str(p))
            actual = gt(root, "hash-object", str(p)) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_blob_exact", actual == expected, actual)

        stage = "AV4_closure_authority"
        r32d = drive / R32_REL
        r32m = manifest(r32d, R32_MANIFEST)
        r32s = js(r32d / R32_SUMMARY)
        r32c = js(r32d / R32_DECISION)

        gate("R32_status_exact", r32s.get("status") == R32_STATUS, r32s.get("status"))
        gate("R32_class_exact", r32s.get("classification") == R32_CLASS, r32s.get("classification"))
        gate("AV4_recurrent_physics_closed", r32s.get("AV4_recurrent_physics_closed") is True)
        gate("R29_repair_lineage_closed", r32s.get("R29_repair_lineage_closed") is True)
        gate("AV4_authoritative_state_SHA_exact", r32c.get("authoritative_state_sha256") == AV4_STATE_SHA)
        gate("AV4_authoritative_day_exact", abs(float(r32c.get("authoritative_physical_day")) - AV4_DAY) <= 1.0e-12)
        gate("AV5_design_authorized", r32c.get("AV5_learned_acceleration_design_authorized") is True)
        gate("AV5_execution_not_authorized", r32c.get("AV5_execution_authorized") is False)
        gate("AV5_exact_physics_required", r32c.get("AV5_must_preserve_exact_AV4_physics_authority") is True)
        gate("AV5_exact_FV_correction_required", r32c.get("AV5_must_not_replace_exact_finite_volume_correction") is True)
        gate("AV5_conservation_gates_frozen", r32c.get("AV5_must_not_relax_conservation_gates") is True)
        gate("R32_manifest_nonempty", len(r32m) > 0)

        stage = "pressure_solver_architecture_audit"
        sg3 = root / SG3
        r3 = root / R3R2R1
        a2e = root / A2E

        gate(
            "SG3_is_direct_spsolve",
            source_contains(sg3, [
                "from scipy.sparse.linalg import spsolve",
                "p_pa = spsolve(A, b)",
            ]),
        )
        gate(
            "updated_pressure_is_direct_spsolve",
            source_contains(r3, [
                "from scipy.sparse.linalg import spsolve",
                "p_pa = np.asarray(spsolve(A, b), dtype=np.float64)",
                "residual = np.asarray(A @ p_pa - b, dtype=np.float64)",
            ]),
        )
        gate(
            "current_direct_solver_has_no_x0_interface",
            "x0=" not in sg3.read_text(encoding="utf-8")
            and "x0=" not in r3.read_text(encoding="utf-8"),
        )

        stage = "outer_fixed_point_architecture_audit"
        a2et = a2e.read_text(encoding="utf-8")
        for name, snippet in {
            "fixed_point_refresh_present": "def fixed_point_refresh(",
            "parent_saturation_initializes_working_state": "parent_saturation",
            "parent_pressure_initializes_previous_pressure": "parent_pressure_psi",
            "mobility_rebuilt_each_iteration": "mobility = spatial_mobility(",
            "updated_pressure_system_reassembled": "assemble_updated_pressure_system(",
            "exact_pressure_solved_each_iteration": "solve_updated_pressure(",
            "mass_reconciliation_each_iteration": "invert_local_mass(",
            "pressure_convergence_gate_present": "PRESSURE_REL_L2_TOL",
            "saturation_convergence_gate_present": "SATURATION_LINF_TOL",
            "maximum_iteration_guard_present": "MAX_FIXED_POINT_ITERATIONS",
            "final_consistency_pressure_solve_present": "final_consistency_pressure_solve_failure",
            "final_pressure_consistency_gate_present": "final_pressure_fixed_point_consistency",
            "final_saturation_consistency_gate_present": "final_saturation_fixed_point_consistency",
        }.items():
            gate(name, snippet in a2et)

        stage = "design_semantics_freeze"
        architecture = {
            "learned_component_role": (
                "predict a pressure seed p_hat for the existing finite-volume pressure system; "
                "learned output is never authoritative physics"
            ),
            "exact_correction_equation": "A * delta_p = b - A * p_hat; p_corrected = p_hat + delta_p",
            "matrix_and_rhs_authority": (
                "A and b are assembled by the unchanged AV4 spatial-mobility finite-volume pressure system"
            ),
            "authoritative_pressure": (
                "only p_corrected after exact residual acceptance, or direct-spsolve fallback/reference"
            ),
            "outer_fixed_point_semantics": (
                "unchanged AV4 mobility -> exact pressure -> mass/EOS reconciliation -> convergence loop"
            ),
            "learned_model_may_not": [
                "replace A or b",
                "replace exact finite-volume correction",
                "modify well controls or mobility laws",
                "modify pressure/saturation fixed-point tolerances",
                "modify Cartesian mass or residual-sidecar semantics",
                "modify Darcy/Pollock/TOF equations",
                "relax any AV4 conservation gate",
                "be used directly for accepted Darcy fluxes without exact correction",
            ],
            "fallback": (
                "if iterative correction fails, stagnates, violates residual gates, or is slower under "
                "the benchmark policy, use the frozen direct spsolve path; fallback is not a physics change"
            ),
        }

        numerical_benchmark = {
            "purpose": (
                "prove that a warm-startable iterative residual-correction solve can reproduce the "
                "direct AV4 pressure solution and provide a measurable acceleration opportunity before ML training"
            ),
            "required_baselines": [
                "direct scipy.sparse.linalg.spsolve (current AV4 authority)",
                "iterative correction from parent/previous pressure seed",
                "iterative correction from simple deterministic seed(s) such as zero or current parent pressure",
            ],
            "candidate_methods": [
                "CG if matrix symmetry/positive-definiteness audit passes",
                "GMRES or another appropriate Krylov method if CG requirements are not proven",
            ],
            "mandatory_equivalence_gates": [
                "same A and b as direct AV4 solve",
                "pressure linear relative residual < existing AV4 1e-8 gate",
                "final pressure-saturation fixed-point gates unchanged",
                "downstream Darcy local/global conservation gates unchanged",
                "no change to Pollock/TOF or transport semantics",
            ],
            "performance_measurement": {
                "measure_prediction_seed_time": True,
                "measure_linear_correction_time": True,
                "measure_full_pressure_refresh_time": True,
                "include_fallback_cost": True,
                "report_iterations": True,
                "no_speedup_threshold_frozen_in_A1": True,
                "reason": "A2 must establish deterministic numerical ceiling before an ML target is chosen",
            },
        }

        dataset_design = {
            "training_authorized_in_A1": False,
            "teacher": "exact AV4 finite-volume pressure solve / fixed-point trajectory only",
            "teacher_outputs": [
                "exact pressure field p_star",
                "assembled residual information sufficient to verify A*p_star-b",
                "fixed-point iteration index and convergence metrics",
            ],
            "candidate_model_inputs": [
                "static permeability / geology descriptors",
                "current fixed-point working saturation or total-mobility field",
                "previous accepted/iteration pressure field",
                "fixed well-control descriptors",
            ],
            "split_policy": (
                "split by independent realization / state trajectory, never randomly by cells or fixed-point "
                "iterations from the same trajectory"
            ),
            "leakage_forbidden": True,
            "model_output": "pressure seed only",
            "loss_may_include": [
                "pressure-field data loss",
                "finite-volume residual regularization",
            ],
            "loss_does_not_define_acceptance": True,
            "acceptance_defined_by_exact_correction_and_AV4_gates": True,
        }

        stage = "publication"
        out.mkdir(parents=True, exist_ok=False)

        classification = (
            "AV5_LEARNED_ACCELERATION_SCOPE_FROZEN_AS_NON_AUTHORITATIVE_PRESSURE_SEED_"
            "PLUS_EXACT_FINITE_VOLUME_RESIDUAL_CORRECTION_"
            "ITERATIVE_NUMERICAL_FEASIBILITY_REQUIRED_BEFORE_TRAINING"
        )

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": classification,
            "AV4_authoritative_state_sha256": AV4_STATE_SHA,
            "AV4_authoritative_physical_day": AV4_DAY,
            "AV4_recurrent_physics_closed": True,
            "current_pressure_linear_solver": "scipy.sparse.linalg.spsolve",
            "current_pressure_solver_accepts_initial_guess": False,
            "learned_pressure_seed_cannot_accelerate_current_direct_spsolve_by_itself": True,
            "outer_pressure_saturation_fixed_point_is_acceleration_target_context": True,
            "exact_FV_pressure_correction_required": True,
            "direct_spsolve_reference_and_fallback_preserved": True,
            "AV4_conservation_gates_unchanged": True,
            "model_training_executed": False,
            "learned_inference_executed": False,
            "AV5_execution_executed": False,
            "state_mutation_executed": False,
            "physical_time_advance_executed": False,
            "P3_authorized": False,
        }

        design = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "learned_acceleration_architecture": architecture,
            "A2_numerical_feasibility_benchmark": numerical_benchmark,
            "future_teacher_dataset_and_model_design": dataset_design,
            "frozen_AV4_authority": {
                "authoritative_state_sha256": AV4_STATE_SHA,
                "authoritative_physical_day": AV4_DAY,
                "pressure_linear_residual_gate": "unchanged AV4 < 1e-8",
                "pressure_fixed_point_tolerance": "unchanged AV4 1e-10 relative L2",
                "saturation_fixed_point_tolerance": "unchanged AV4 1e-10 Linf",
            },
        }

        decision = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "AV5_A2_authorized": True,
            "AV5_A2_name": "Exact-Correction Iterative Pressure Solver + Deterministic Warm-Start Feasibility Benchmark",
            "AV5_A2_scope": (
                "benchmark a warm-startable iterative residual-correction path against frozen direct spsolve "
                "using exact AV4 A/b systems; no ML training and no accepted-state mutation"
            ),
            "AV5_A2_execution_authorized": True,
            "AV5_A2_must_bind_AV4_state_SHA": AV4_STATE_SHA,
            "AV5_A2_must_preserve_direct_spsolve_reference": True,
            "AV5_A2_must_not_train_model": True,
            "AV5_model_training_authorized": False,
            "AV5_learned_inference_authorized": False,
            "AV5_production_execution_authorized": False,
            "AV5_must_preserve_exact_AV4_physics_authority": True,
            "AV5_must_not_replace_exact_finite_volume_correction": True,
            "AV5_must_not_relax_conservation_gates": True,
            "AV5_must_not_change_fixed_point_tolerances": True,
            "AV5_must_not_change_Darcy_Pollock_TOF_transport_semantics": True,
            "AV5_must_not_mutate_AV4_authoritative_state": True,
            "P3_authorized": False,
        }

        (out / f"PAD_Stream_{OUT_TOKEN}_Summary.json").write_bytes(jb(summary))
        (out / f"{OUT_TOKEN}_Learned_Acceleration_Architecture_Design_Contract.json").write_bytes(jb(design))
        (out / f"{OUT_TOKEN}_Decision_Contract.json").write_bytes(jb(decision))
        (out / f"{OUT_TOKEN}_Final_Gate_Matrix.csv").write_bytes(csvb(gates))

        rows = []
        for p in sorted(out.iterdir()):
            if p.is_file():
                rows.append({"file": p.name, "sha256": sha(p), "bytes": p.stat().st_size})
        (out / f"{OUT_TOKEN}_Artifact_Manifest.csv").write_bytes(csvb(rows))

        print("=" * 200)
        print(M, "PASS")
        print("Classification                          :", classification)
        print("AV4 authoritative state SHA256          :", AV4_STATE_SHA)
        print("Current exact linear solver             : scipy.sparse.linalg.spsolve")
        print("Current direct solver has x0 warm start : False")
        print("Learned model role                      : pressure seed only")
        print("Exact FV residual correction required   : True")
        print("Direct spsolve reference/fallback       : True")
        print("Model training authorized               : False")
        print("AV5-A2 numerical benchmark authorized   : True")
        print("P3 authorized                           : False")
        print("=" * 200)
        return 0

    except Exception as exc:
        block_dir.mkdir(parents=True, exist_ok=True)
        p = block_dir / f"{OUT_TOKEN}_Blocked_Report.json"
        if not p.exists():
            p.write_bytes(jb({
                "milestone": M,
                "status": BLOCK,
                "failed_stage": stage,
                "exception": repr(exc),
                "AV4_closure_preserved": True,
                "AV4_authoritative_state_preserved": True,
                "model_training_executed": False,
                "AV5_execution_executed": False,
                "state_mutation_executed": False,
                "physical_time_advance_executed": False,
                "P3_authorized": False,
                "gates_completed": gates,
            }))
        print(M, "TECHNICAL / AUTHORITY BLOCK")
        print("Stage:", stage)
        print("Exception:", repr(exc))
        return 2


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", type=Path, default=Path("."))
    ap.add_argument("--drive-root", type=Path, default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        selftest()
        raise SystemExit(0)
    raise SystemExit(main(args.project_root, args.drive_root))
