from __future__ import annotations

from pathlib import Path
import argparse
import csv
import hashlib
import io
import json
import subprocess
import sys
from typing import Any

MILESTONE = "V16E-41-R3-R6"
STATUS = "PRODUCTION_RUNTIME_REFRESH_POLICY_FROZEN"
NEXT = "V16E-41-R3-R7 - Repaired Production Rollout to Exact 100-Day Observation"

EXPECTED_R3R5_STATUS = "MULTI_REFRESH_CADENCE_SENSITIVITY_RUNTIME_POLICY_CALIBRATED"
EXPECTED_SELECTED_POLICY = "HALF_OBSERVED_STALE_INTERVAL"
EXPECTED_SELECTED_MAX_EPOCH_DAYS = 4.9417335239115445
EXPECTED_R3R5_SELECTED_CALIBRATION_SHA = "7ca6f0b8fbbf08608d4ddc6cc136e4cfcd5cbb3e609762412e1ba861ef41a0fb"

R3R5_RUNNER = "PAD_Stream_V16E41R3R5_Multi_Refresh_Cadence_Sensitivity_Runtime_Refresh_Policy_Calibration.py"
R3R5_GIT_BLOB = "15aae3224ba4337cad72f9b4aa9166d602791349"
R3R3_RUNNER = "PAD_Stream_V16E41R3R3_Saturation_Updated_Flow_Refresh_Runtime_Architecture_Freeze.py"
R3R3_GIT_BLOB = "8d72895d023fe6c2d7d3c9752698a557747117a8"
R3R3R1_RUNNER = "PAD_Stream_V16E41R3R3R1_Mass_Conservative_Pressure_Refresh_Reconciliation_Architecture_Amendment.py"
R3R3R1_GIT_BLOB = "8087c864e85351859c771f744b81e82f995d6581"
R3R4R1_RUNNER = "PAD_Stream_V16E41R3R4R1_Refreshed_Flow_CFL_Alignment_Repair.py"
R3R4R1_GIT_BLOB = "5f8433437ce111533338ceada922f51abb2edefe"

R3R5_REL = Path("provenance/hybrid_dp/V16E41R3R5_MULTI_REFRESH_CADENCE_SENSITIVITY_RUNTIME_POLICY_CALIBRATION")
R3R5_SUMMARY = "PAD_Stream_V16E41R3R5_Summary.json"
R3R5_CLOSURE = "V16E41R3R5_Final_Closure.json"
R3R3_REL = Path("provenance/hybrid_dp/V16E41R3R3_SATURATION_UPDATED_FLOW_REFRESH_RUNTIME_ARCHITECTURE_FREEZE")
R3R3_CONTRACT = "PAD_Stream_V16E41R3R3_Architecture_Contract.json"
R3R3R1_REL = Path("provenance/hybrid_dp/V16E41R3R3R1_MASS_CONSERVATIVE_PRESSURE_REFRESH_RECONCILIATION_ARCHITECTURE_AMENDMENT")
R3R3R1_CONTRACT = "PAD_Stream_V16E41R3R3R1_Reconciliation_Architecture_Amendment.json"
R3R4R1_REL = Path("provenance/hybrid_dp/V16E41R3R4R1_REFRESHED_FLOW_CFL_ALIGNMENT_REPAIR")
R3R4R1_SUMMARY = "PAD_Stream_V16E41R3R4R1_Summary.json"
OUT_REL = Path("provenance/hybrid_dp/V16E41R3R6_PRODUCTION_RUNTIME_REFRESH_POLICY_FREEZE")

HARD_REFRESH_TRIGGERS = [
    "RESTART_OR_INITIALIZATION",
    "WELL_OR_CONTROL_CHANGE",
    "POST_OBSERVATION_CHECKPOINT",
    "CAPACITY_PREFLIGHT_REJECTION",
]
TIMESTEP_PRECEDENCE = [
    "EXACT_OBSERVATION_OR_EVENT_LANDING",
    "MAX_FLOW_EPOCH_AGE_BOUNDARY",
    "REFRESHED_FLOW_CFL",
    "CAPACITY_FALLBACK_ONLY_AFTER_SAME_PARENT_REFRESH",
]

class GateError(RuntimeError):
    pass

def json_bytes(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True) + "\n").encode("utf-8")

def csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        return b""
    fields = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue().encode("utf-8")

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()

def immutable_publish(out: Path, files: dict[str, bytes]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        p = out / name
        if p.exists():
            if p.read_bytes() != data:
                raise GateError(f"existing_output_differs:{name}")
        else:
            p.write_bytes(data)

def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def git_blob_sha(path: Path, repo_root: Path) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "hash-object", str(path)],
        check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    return proc.stdout.strip()

def self_test() -> None:
    if EXPECTED_SELECTED_POLICY != "HALF_OBSERVED_STALE_INTERVAL":
        raise RuntimeError("selected_policy_identity")
    if abs(EXPECTED_SELECTED_MAX_EPOCH_DAYS - 4.9417335239115445) > 1e-15:
        raise RuntimeError("selected_epoch_identity")
    if len(HARD_REFRESH_TRIGGERS) != 4:
        raise RuntimeError("hard_trigger_count")
    if TIMESTEP_PRECEDENCE[-1] != "CAPACITY_FALLBACK_ONLY_AFTER_SAME_PARENT_REFRESH":
        raise RuntimeError("capacity_fallback_precedence")
    print("PAD-Stream V16E-41-R3-R6 production runtime refresh policy freeze self-test: PASS")

def main(project_root: Path, drive_root: Path) -> int:
    root = Path(project_root).resolve()
    drive = Path(drive_root).resolve()
    out = drive / OUT_REL
    gates: dict[str, dict[str, Any]] = {}

    def gate(name: str, passed: bool, detail: Any = "") -> None:
        gates[name] = {"passed": bool(passed), "detail": str(detail)}
        if not passed:
            raise GateError(name)

    print("\n" + "=" * 154)
    print("PAD-Stream V16E-41-R3-R6 — Production Runtime Refresh Policy Freeze")
    print("=" * 154)

    source_bindings = {
        "R3R5": (R3R5_RUNNER, R3R5_GIT_BLOB),
        "R3R3": (R3R3_RUNNER, R3R3_GIT_BLOB),
        "R3R3R1": (R3R3R1_RUNNER, R3R3R1_GIT_BLOB),
        "R3R4R1": (R3R4R1_RUNNER, R3R4R1_GIT_BLOB),
    }
    source_rows = []
    for role, (filename, expected_blob) in source_bindings.items():
        p = root / filename
        gate(f"{role}_runner_exists", p.is_file(), p)
        actual = git_blob_sha(p, root)
        gate(f"{role}_git_blob_exact", actual == expected_blob, actual)
        source_rows.append({
            "role": role, "filename": filename,
            "expected_git_blob": expected_blob, "actual_git_blob": actual
        })

    paths = [
        drive / R3R5_REL / R3R5_SUMMARY,
        drive / R3R5_REL / R3R5_CLOSURE,
        drive / R3R3_REL / R3R3_CONTRACT,
        drive / R3R3R1_REL / R3R3R1_CONTRACT,
        drive / R3R4R1_REL / R3R4R1_SUMMARY,
    ]
    for p in paths:
        gate(f"artifact_exists_{p.name}", p.is_file(), p)

    r3r5 = load_json(paths[0])
    r3r5_closure = load_json(paths[1])
    r3r3 = load_json(paths[2])
    r3r3r1 = load_json(paths[3])
    r3r4r1 = load_json(paths[4])

    gate("R3R5_status_exact", r3r5.get("status") == EXPECTED_R3R5_STATUS, r3r5.get("status"))
    gate("R3R5_closure_passed", r3r5_closure.get("all_gates_passed") is True, r3r5_closure.get("all_gates_passed"))
    gate("R3R5_selected_policy_exact", r3r5.get("selected_policy") == EXPECTED_SELECTED_POLICY, r3r5.get("selected_policy"))
    gate("R3R5_selected_epoch_exact", abs(float(r3r5.get("selected_max_flow_epoch_days")) - EXPECTED_SELECTED_MAX_EPOCH_DAYS) <= 1e-15, r3r5.get("selected_max_flow_epoch_days"))
    gate("R3R5_selected_calibration_SHA_exact", r3r5.get("selected_calibration_state_sha256") == EXPECTED_R3R5_SELECTED_CALIBRATION_SHA, r3r5.get("selected_calibration_state_sha256"))
    gate(
        "R3R5_all_finite_policies_passed",
        r3r5.get("finite_policies_passing") == [
            "HALF_OBSERVED_STALE_INTERVAL",
            "QUARTER_OBSERVED_STALE_INTERVAL",
            "EIGHTH_OBSERVED_STALE_INTERVAL",
        ],
        r3r5.get("finite_policies_passing"),
    )
    selected_metrics = r3r5["selected_policy_terminal_metrics"]
    gate("R3R5_selected_capacity_refreshes_zero", int(selected_metrics["capacity_refresh_count"]) == 0, selected_metrics["capacity_refresh_count"])
    gate("R3R5_selected_capacity_margin_positive", float(selected_metrics["min_raw_capacity_margin_kg"]) > 0.0, selected_metrics["min_raw_capacity_margin_kg"])
    gate("R3R5_policy_not_pre_frozen", r3r5.get("production_policy_frozen") is False, r3r5.get("production_policy_frozen"))
    gate("R3R5_100d_not_pre_authorized", r3r5.get("100d_rollout_authorized") is False, r3r5.get("100d_rollout_authorized"))

    original_triggers = list(r3r3.get("hard_refresh_triggers", []))
    gate("R3R3_hard_trigger_set_exact", original_triggers == HARD_REFRESH_TRIGGERS, original_triggers)
    gate(
        "R3R3R1_primary_conserved_quantity_cellwise_mass",
        r3r3r1.get("primary_conserved_refresh_quantity") == "cellwise Cartesian CO2 component mass array",
        r3r3r1.get("primary_conserved_refresh_quantity"),
    )
    gate(
        "R3R4R1_status_exact",
        r3r4r1.get("status") == "SAME_PARENT_MASS_CONSERVATIVE_REFRESHED_FLOW_CFL_ALIGNED_TRANSITION_VALIDATED",
        r3r4r1.get("status"),
    )
    gate(
        "R3R4R1_capacity_dt_reduction_unused",
        r3r4r1["same_parent_candidate"]["capacity_timestep_reduction_used"] is False,
        r3r4r1["same_parent_candidate"]["capacity_timestep_reduction_used"],
    )

    contract = {
        "milestone": MILESTONE,
        "status": STATUS,
        "purpose": "Freeze the single production runtime refresh policy for the repaired exact-100-day E41 rollout and subsequent V16 observation sequence.",
        "calibrated_policy": {
            "name": EXPECTED_SELECTED_POLICY,
            "maximum_flow_epoch_age_days": EXPECTED_SELECTED_MAX_EPOCH_DAYS,
            "selection_basis": "Coarsest finite R3-R5 cadence satisfying every predeclared convergence gate against the finest finite reference.",
            "R3R5_selected_calibration_state_sha256": EXPECTED_R3R5_SELECTED_CALIBRATION_SHA,
            "R3R5_selected_capacity_refresh_count": int(selected_metrics["capacity_refresh_count"]),
            "R3R5_selected_minimum_raw_capacity_margin_kg": float(selected_metrics["min_raw_capacity_margin_kg"]),
        },
        "refresh_trigger_policy": {
            "maximum_epoch_age_trigger": {
                "enabled": True,
                "age_days": EXPECTED_SELECTED_MAX_EPOCH_DAYS,
                "action": "Land exactly on the cadence boundary when needed, then perform a same-time full flow refresh.",
            },
            "hard_refresh_triggers": HARD_REFRESH_TRIGGERS,
            "hard_triggers_override_cadence": True,
            "post_observation_refresh_required": True,
        },
        "same_time_flow_refresh_contract": {
            "physical_time_advance": False,
            "accepted_step_advance": False,
            "cumulative_injection_change": False,
            "cumulative_production_change": False,
            "external_mass_source_sink": False,
            "primary_conserved_quantity": "cellwise Cartesian CO2 component mass array",
            "p_ref_change_authorized": False,
            "spatial_mass_redistribution_authorized": False,
            "saturation_may_change_same_time": True,
            "reason_saturation_may_change": "Thermodynamic pressure/density reconciliation of the same cellwise component mass; not transport.",
            "pressure_saturation_solver": {
                "method": "direct Picard fixed point",
                "hidden_damping_authorized": False,
                "pressure_relative_L2_tolerance": 1e-10,
                "saturation_Linf_tolerance": 1e-10,
                "maximum_iterations": 100,
                "failure_action": "BLOCK_AND_AUDIT",
            },
            "flow_epoch_build_sequence": [
                "total_mobility_from_reconciled_saturation",
                "finite_volume_pressure",
                "conservative_Darcy_face_fluxes",
                "exact_Pollock_streamlines",
                "time_of_flight",
                "SG7D_overlap",
                "E37A_control_volume_geometry",
                "streamline_face_pressure",
            ],
        },
        "transport_timestep_policy": {
            "precedence": TIMESTEP_PRECEDENCE,
            "normal_trial_dt_definition": "Largest positive local dt that lands on the next required observation/event or cadence boundary and does not exceed the active refreshed-flow CFL.",
            "old_same_candidate_retry_clause_superseded": True,
            "superseding_rule": "After any same-parent flow refresh, preserve the same intended transport horizon but recompute actual retry dt so it does not exceed refreshed-flow CFL.",
            "observation_landing_exact": True,
            "cadence_boundary_landing_exact": True,
            "canonical_temporal_interpolation_authorized": False,
        },
        "capacity_safety_policy": {
            "raw_mapback_capacity_preflight_required": True,
            "first_capacity_failure_action": "Reject uncommitted trial, roll back to exact accepted parent, perform full mass-conservative flow refresh, recompute refreshed-flow CFL, and retry from same parent.",
            "if_still_capacity_unsafe_after_refresh": "Invoke validated R2 capacity-aware timestep controller only as last-resort safety fallback.",
            "capacity_limited_accepted_transition_post_action": "Force immediate full flow refresh before next physical transition.",
            "capacity_controller_is_normal_timestep_driver": False,
            "saturation_ceiling_relaxation_authorized": False,
            "mass_clipping_authorized": False,
            "artificial_mass_source_sink_authorized": False,
            "global_plume_rescaling_authorized": False,
        },
        "accepted_transition_contract": {
            "component_mass_primary_conserved_variable": True,
            "conservative_grid_to_streamline_sampling_required": True,
            "conservative_CV_transport_required": True,
            "conservative_streamline_to_grid_mapback_required": True,
            "no_flow_capillary_external_mass_exact_zero_required": True,
            "component_mass_closure_required": True,
            "rejection_advances_time": False,
            "rejection_advances_step": False,
            "rejection_advances_recurrent_memory": False,
        },
        "production_observation_policy": {
            "observation_days": [30, 60, 100, 150, 250, 365, 500, 750, 1000],
            "next_required_target_day": 100,
            "R3R5_80d_calibration_state_is_canonical": False,
            "100d_rollout_now_authorized": True,
            "100d_regression_authorized_before_R3R7_pass": False,
        },
        "scope_guards": {
            "production_policy_frozen": True,
            "new_calibration_branch_authorized": False,
            "new_mapping_algorithm_authorized": False,
            "new_streamline_algorithm_authorized": False,
            "new_ML_module_authorized": False,
            "IBDP_work_authorized_before_V16_closeout": False,
            "exception": "Only a genuinely new physics/numerical defect exposed by the frozen production runtime may justify a targeted repair.",
        },
        "V16_closeout_visuals_required": [
            "SGSim reservoir geometry and permeability heterogeneity",
            "pressure field",
            "Darcy face fluxes",
            "Pollock streamlines",
            "time-of-flight field",
            "CO2 plume evolution at V16 observation checkpoints",
            "PAD-Stream full architecture and runtime flow",
        ],
        "next_milestone": NEXT,
    }

    gate("contract_policy_frozen", contract["scope_guards"]["production_policy_frozen"] is True)
    gate("contract_selected_epoch_exact", contract["calibrated_policy"]["maximum_flow_epoch_age_days"] == EXPECTED_SELECTED_MAX_EPOCH_DAYS)
    gate("contract_hard_triggers_exact", contract["refresh_trigger_policy"]["hard_refresh_triggers"] == HARD_REFRESH_TRIGGERS)
    gate("contract_refreshed_CFL_supersedes_old_same_dt_clause", contract["transport_timestep_policy"]["old_same_candidate_retry_clause_superseded"] is True)
    gate("contract_capacity_controller_fallback_only", contract["capacity_safety_policy"]["capacity_controller_is_normal_timestep_driver"] is False)
    gate("contract_100d_rollout_authorized", contract["production_observation_policy"]["100d_rollout_now_authorized"] is True)
    gate("contract_100d_regression_still_not_authorized", contract["production_observation_policy"]["100d_regression_authorized_before_R3R7_pass"] is False)

    closure = {
        "milestone": MILESTONE,
        "status": STATUS,
        "all_gates_passed": all(v["passed"] for v in gates.values()),
        "gate_count": len(gates),
        "selected_policy": EXPECTED_SELECTED_POLICY,
        "maximum_flow_epoch_age_days": EXPECTED_SELECTED_MAX_EPOCH_DAYS,
        "hard_refresh_triggers": HARD_REFRESH_TRIGGERS,
        "refreshed_CFL_after_refresh_required": True,
        "capacity_controller_fallback_only": True,
        "production_policy_frozen": True,
        "exact_100d_rollout_authorized": True,
        "100d_legacy_regression_authorized": False,
        "next_milestone": NEXT,
    }

    files = {
        "PAD_Stream_V16E41R3R6_Production_Runtime_Refresh_Policy_Contract.json": json_bytes(contract),
        "V16E41R3R6_Source_Bindings.csv": csv_bytes(source_rows),
        "V16E41R3R6_Final_Gate_Matrix.csv": csv_bytes([{"gate": k, **v} for k, v in gates.items()]),
        "V16E41R3R6_Final_Closure.json": json_bytes(closure),
    }
    immutable_publish(out, files)

    manifest = []
    for p in sorted(out.iterdir()):
        if p.is_file() and p.name != "V16E41R3R6_Artifact_Manifest.csv":
            manifest.append({"file": p.name, "sha256": sha256_file(p), "bytes": p.stat().st_size})
    immutable_publish(out, {"V16E41R3R6_Artifact_Manifest.csv": csv_bytes(manifest)})

    print("\n" + "=" * 154)
    print("PAD-Stream V16E-41-R3-R6: PASS")
    print("=" * 154)
    print(f"{'Status':64}: {STATUS}")
    print(f"{'Selected production policy':64}: {EXPECTED_SELECTED_POLICY}")
    print(f"{'Maximum flow-epoch age':64}: {EXPECTED_SELECTED_MAX_EPOCH_DAYS:.16g} d")
    print(f"{'Hard refresh triggers':64}: {HARD_REFRESH_TRIGGERS}")
    print(f"{'Refreshed CFL required after refresh':64}: True")
    print(f"{'Capacity controller role':64}: fallback only")
    print(f"{'Production policy frozen':64}: True")
    print(f"{'Exact 100-day rollout authorized':64}: True")
    print(f"{'100-day legacy regression authorized':64}: False")
    print(f"{'Next':64}: {NEXT}")
    return 0

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--project-root", type=Path, default=Path("."))
    p.add_argument("--drive-root", type=Path, default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    p.add_argument("--self-test", action="store_true")
    return p.parse_args()

if __name__ == "__main__":
    args = parse_args()
    if args.self_test:
        self_test()
        raise SystemExit(0)
    raise SystemExit(main(args.project_root, args.drive_root))
