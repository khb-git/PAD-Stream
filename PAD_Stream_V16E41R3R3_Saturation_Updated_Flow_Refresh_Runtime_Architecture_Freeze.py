from __future__ import annotations

from pathlib import Path
import argparse
import csv
import hashlib
import json
from typing import Any


MILESTONE = "V16E-41-R3-R3"
STATUS = "SATURATION_UPDATED_FLOW_REFRESH_RUNTIME_ARCHITECTURE_FROZEN"
NEXT = (
    "V16E-41-R3-R4 - Controlled Same-Parent Saturation-Updated "
    "Flow-Refresh Transition Validation"
)

R3R2R1_REL = Path(
    "provenance/hybrid_dp/"
    "V16E41R3R2R1_LOCAL_CONSERVATION_SIGN_CONVENTION_REPAIR"
)
R3R2R1_SUMMARY = "PAD_Stream_V16E41R3R2R1_Summary.json"
R3R2R1_CLOSURE = "V16E41R3R2R1_Final_Closure.json"

OUT_REL = Path(
    "provenance/hybrid_dp/"
    "V16E41R3R3_SATURATION_UPDATED_FLOW_REFRESH_RUNTIME_ARCHITECTURE_FREEZE"
)
BLOCKED_REL = Path(
    "provenance/hybrid_dp/"
    "V16E41R3R3_BLOCKED_SATURATION_UPDATED_FLOW_REFRESH_RUNTIME_ARCHITECTURE_FREEZE"
)

# Exact published predecessor runner blob on GitHub main.
R3R2R1_RUNNER = (
    "PAD_Stream_V16E41R3R2R1_Local_Conservation_Sign_Convention_Repair.py"
)
R3R2R1_GIT_BLOB = "740c6da03e73906646bf0153633187e749449f31"

EXPECTED_R3R2R1_STATUS = (
    "SATURATION_UPDATED_FLOW_STREAMLINE_CAPACITY_FEASIBILITY_AUDITED_R1"
)
EXPECTED_DIAGNOSIS = "UPDATED_FLOW_NATURALLY_REMOVES_MAPBACK_CAPACITY_LOCK"

EXPECTED_STEP = 3975
EXPECTED_TIME_DAYS = 69.88346704782309
EXPECTED_STATE_SHA256 = (
    "8714f5b35b99472de0251def022043076f85fb9cee2ada1cfc4d7b7441cce5e6"
)

EXPECTED_PRESSURE_REL_L2 = 0.29988818649080956
EXPECTED_LOCAL_FLOW_RESIDUAL = 2.6711219248769463e-13
EXPECTED_GLOBAL_FLOW_RESIDUAL = 1.3953032388596096e-13
EXPECTED_UPDATED_SEEDS = 1078
EXPECTED_UPDATED_CAPTURE = 1.0
EXPECTED_LIMITER_INFLOW_REDUCTION = -0.06327757183524274
EXPECTED_FROZEN_OVERCAPACITY_CELLS = 1
EXPECTED_UPDATED_OVERCAPACITY_CELLS = 0
EXPECTED_FROZEN_LIMITER_EXCESS_KG = 6.098388866071673
EXPECTED_UPDATED_LIMITER_EXCESS_KG = -11.199047942100151

# The stale-flow interval observed from the authoritative 60 d checkpoint
# to the R3-R1 capacity-lock state. We use it only to define a later
# cadence-sensitivity ladder; it is NOT a production refresh interval.
E40_REFERENCE_DAY = 60.0
OBSERVED_STALE_INTERVAL_DAYS = EXPECTED_TIME_DAYS - E40_REFERENCE_DAY

CADENCE_CANDIDATES_DAYS = {
    "EVENT_ONLY_BASELINE": None,
    "HALF_OBSERVED_STALE_INTERVAL": OBSERVED_STALE_INTERVAL_DAYS / 2.0,
    "QUARTER_OBSERVED_STALE_INTERVAL": OBSERVED_STALE_INTERVAL_DAYS / 4.0,
    "EIGHTH_OBSERVED_STALE_INTERVAL": OBSERVED_STALE_INTERVAL_DAYS / 8.0,
}


class GateError(RuntimeError):
    pass


def json_bytes(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True) + "\n").encode("utf-8")


def csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        return b""
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    import io
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


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def git_blob_sha(path: Path, repo_root: Path) -> str:
    import subprocess
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "hash-object", str(path)],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return proc.stdout.strip()


def immutable_publish(out: Path, files: dict[str, bytes]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        p = out / name
        if p.exists():
            if p.read_bytes() != data:
                raise GateError(f"existing_output_differs:{name}")
        else:
            p.write_bytes(data)


def near(a: float, b: float, atol: float = 1.0e-12, rtol: float = 1.0e-10) -> bool:
    return abs(float(a) - float(b)) <= atol + rtol * max(abs(float(a)), abs(float(b)), 1.0)


def self_test() -> None:
    stale = 69.88346704782309 - 60.0
    vals = [stale / 2.0, stale / 4.0, stale / 8.0]
    if not (vals[0] > vals[1] > vals[2] > 0.0):
        raise RuntimeError("self_test_cadence_ladder")

    priority = [
        "RESTART_OR_INITIALIZATION",
        "WELL_OR_CONTROL_CHANGE",
        "POST_OBSERVATION_CHECKPOINT",
        "CAPACITY_PREFLIGHT_REJECTION",
        "CALIBRATED_MAX_FLOW_EPOCH",
    ]
    if len(priority) != len(set(priority)):
        raise RuntimeError("self_test_trigger_priority_unique")

    print(
        "PAD-Stream V16E-41-R3-R3 saturation-updated flow-refresh "
        "runtime architecture freeze self-test: PASS"
    )


def main(project_root: Path, drive_root: Path) -> int:
    root = Path(project_root).resolve()
    drive = Path(drive_root).resolve()
    out = drive / OUT_REL
    blocked = drive / BLOCKED_REL

    gates: dict[str, dict[str, Any]] = {}
    failed_stage: str | None = None

    def gate(name: str, passed: bool, detail: Any = "") -> None:
        gates[name] = {"passed": bool(passed), "detail": str(detail)}
        if not passed:
            raise GateError(name)

    try:
        print("\n" + "=" * 154)
        print(
            "PAD-Stream V16E-41-R3-R3 — Saturation-Updated "
            "Flow-Refresh Runtime Architecture Freeze"
        )
        print("=" * 154)
        print("ROLE       : architecture / state-machine contract only")
        print("SOLVER RUN : none")
        print("STATE MOVE : none")
        print("100D CLAIM : none")
        print(
            "PURPOSE    : freeze recurrent pressure/flux/streamline/TOF "
            "refresh semantics before controlled implementation"
        )

        failed_stage = "R3R2R1_provenance_binding"

        pred_runner = root / R3R2R1_RUNNER
        gate("R3R2R1_runner_exists", pred_runner.is_file(), pred_runner)
        actual_blob = git_blob_sha(pred_runner, root)
        gate(
            "R3R2R1_runner_git_blob_exact",
            actual_blob == R3R2R1_GIT_BLOB,
            actual_blob,
        )

        summary_path = drive / R3R2R1_REL / R3R2R1_SUMMARY
        closure_path = drive / R3R2R1_REL / R3R2R1_CLOSURE
        gate("R3R2R1_summary_exists", summary_path.is_file(), summary_path)
        gate("R3R2R1_closure_exists", closure_path.is_file(), closure_path)

        summary = load_json(summary_path)
        closure = load_json(closure_path)

        gate(
            "R3R2R1_status_exact",
            summary.get("status") == EXPECTED_R3R2R1_STATUS,
            summary.get("status"),
        )
        gate(
            "R3R2R1_closure_passed",
            closure.get("all_audit_gates_passed") is True,
            closure.get("all_audit_gates_passed"),
        )
        gate(
            "R3R2R1_diagnosis_exact",
            summary.get("diagnosis") == EXPECTED_DIAGNOSIS,
            summary.get("diagnosis"),
        )
        gate(
            "R3R2R1_input_step_exact",
            int(summary.get("input_partial_state_step", -1)) == EXPECTED_STEP,
            summary.get("input_partial_state_step"),
        )
        gate(
            "R3R2R1_input_time_exact",
            near(summary.get("input_partial_state_time_days"), EXPECTED_TIME_DAYS),
            summary.get("input_partial_state_time_days"),
        )
        gate(
            "R3R2R1_input_state_SHA_exact",
            summary.get("input_partial_state_sha256") == EXPECTED_STATE_SHA256,
            summary.get("input_partial_state_sha256"),
        )
        gate(
            "R3R2R1_pressure_change_binding",
            near(
                summary.get("updated_pressure_relative_L2_vs_frozen"),
                EXPECTED_PRESSURE_REL_L2,
            ),
            summary.get("updated_pressure_relative_L2_vs_frozen"),
        )

        flow = summary.get("updated_flow_conservation", {})
        gate(
            "R3R2R1_local_conservation_binding",
            near(
                flow.get("local_relative_l2_error"),
                EXPECTED_LOCAL_FLOW_RESIDUAL,
                atol=1.0e-14,
                rtol=1.0e-8,
            ),
            flow.get("local_relative_l2_error"),
        )
        gate(
            "R3R2R1_global_conservation_binding",
            near(
                flow.get("global_relative_mismatch"),
                EXPECTED_GLOBAL_FLOW_RESIDUAL,
                atol=1.0e-14,
                rtol=1.0e-8,
            ),
            flow.get("global_relative_mismatch"),
        )
        gate(
            "R3R2R1_updated_seed_count",
            int(summary.get("updated_streamline_seed_count", -1))
            == EXPECTED_UPDATED_SEEDS,
            summary.get("updated_streamline_seed_count"),
        )
        gate(
            "R3R2R1_capture_fraction",
            near(
                summary.get("updated_streamline_capture_fraction"),
                EXPECTED_UPDATED_CAPTURE,
                atol=1.0e-14,
                rtol=0.0,
            ),
            summary.get("updated_streamline_capture_fraction"),
        )
        gate(
            "R3R2R1_limiter_inflow_change_binding",
            near(
                summary.get("limiter_inflow_fraction_reduction"),
                EXPECTED_LIMITER_INFLOW_REDUCTION,
            ),
            summary.get("limiter_inflow_fraction_reduction"),
        )

        frozen_cap = summary.get("frozen_nominal_capacity_audit", {})
        updated_cap = summary.get("updated_nominal_capacity_audit", {})
        gate(
            "R3R2R1_frozen_overcapacity_count",
            int(frozen_cap.get("overcapacity_cell_count", -1))
            == EXPECTED_FROZEN_OVERCAPACITY_CELLS,
            frozen_cap.get("overcapacity_cell_count"),
        )
        gate(
            "R3R2R1_updated_overcapacity_count",
            int(updated_cap.get("overcapacity_cell_count", -1))
            == EXPECTED_UPDATED_OVERCAPACITY_CELLS,
            updated_cap.get("overcapacity_cell_count"),
        )
        gate(
            "R3R2R1_frozen_limiter_excess",
            near(
                frozen_cap.get("limiter_cell_excess_kg"),
                EXPECTED_FROZEN_LIMITER_EXCESS_KG,
            ),
            frozen_cap.get("limiter_cell_excess_kg"),
        )
        gate(
            "R3R2R1_updated_limiter_margin",
            near(
                updated_cap.get("limiter_cell_excess_kg"),
                EXPECTED_UPDATED_LIMITER_EXCESS_KG,
            ),
            updated_cap.get("limiter_cell_excess_kg"),
        )
        gate(
            "R3R2R1_updated_raw_mapback_safe",
            int(updated_cap.get("overcapacity_cell_count", -1)) == 0,
            updated_cap.get("overcapacity_cell_count"),
        )

        failed_stage = "architecture_contract_freeze"

        refresh_pipeline = [
            {
                "order": 1,
                "stage": "TOTAL_MOBILITY_FROM_ACCEPTED_GRID_STATE",
                "rule": (
                    "Compute two-phase total mobility from the accepted Cartesian "
                    "saturation state using the frozen Corey/viscosity convention."
                ),
            },
            {
                "order": 2,
                "stage": "FINITE_VOLUME_PRESSURE_SOLVE",
                "rule": (
                    "Solve pressure on the SGSim grid with fixed-rate injector, "
                    "BHP producers, anisotropic permeability, and accepted gravity convention."
                ),
            },
            {
                "order": 3,
                "stage": "CONSERVATIVE_DARCY_FACE_FLUXES",
                "rule": (
                    "Recompute Qx/Qy/Qz and require local/global finite-volume conservation."
                ),
            },
            {
                "order": 4,
                "stage": "EXACT_POLLOCK_RETRACE",
                "rule": (
                    "Rebuild flux-weighted injector seeds and trace exact Pollock streamlines."
                ),
            },
            {
                "order": 5,
                "stage": "TOF_RECONSTRUCTION",
                "rule": (
                    "Recompute physical time-of-flight and normalized transport coordinates."
                ),
            },
            {
                "order": 6,
                "stage": "EXACT_SG7D_OVERLAP_REBUILD",
                "rule": (
                    "Rebuild Cartesian subsegment overlap and E37A control-volume geometry."
                ),
            },
            {
                "order": 7,
                "stage": "FLOW_EPOCH_COMMIT",
                "rule": (
                    "Only after all flow-refresh gates pass may the new pressure/flux/"
                    "streamline/TOF/overlap bundle become the active flow epoch."
                ),
            },
        ]

        trigger_rows = [
            {
                "priority": 1,
                "trigger": "RESTART_OR_INITIALIZATION",
                "hard_or_calibrated": "HARD",
                "action": "REFRESH_BEFORE_ANY_TRANSPORT",
                "reason": "A flow epoch must be derived from its accepted grid state.",
            },
            {
                "priority": 2,
                "trigger": "WELL_OR_CONTROL_CHANGE",
                "hard_or_calibrated": "HARD",
                "action": "REFRESH_BEFORE_NEXT_TRANSPORT",
                "reason": "Changed rate/BHP/schedule invalidates the previous pressure field.",
            },
            {
                "priority": 3,
                "trigger": "POST_OBSERVATION_CHECKPOINT",
                "hard_or_calibrated": "HARD",
                "action": "REFRESH_BEFORE_CONTINUING_TO_NEXT_OBSERVATION_INTERVAL",
                "reason": "Observation state is an exact synchronization point.",
            },
            {
                "priority": 4,
                "trigger": "CAPACITY_PREFLIGHT_REJECTION",
                "hard_or_calibrated": "HARD",
                "action": "REFRESH_FROM_SAME_PARENT_BEFORE_DT_REDUCTION",
                "reason": (
                    "R3-R2-R1 proved the 69.883 d lock was removed by a "
                    "saturation-updated flow field."
                ),
            },
            {
                "priority": 5,
                "trigger": "CALIBRATED_MAX_FLOW_EPOCH",
                "hard_or_calibrated": "CALIBRATION_REQUIRED",
                "action": "REFRESH_BEFORE_NEXT_TRANSPORT",
                "reason": (
                    "Prevent stale mobility/velocity fields before a hard capacity "
                    "event; cadence is selected only after sensitivity testing."
                ),
            },
        ]

        state_machine_rows = [
            {
                "state": "FLOW_REFRESH_REQUIRED",
                "allowed_next": "BUILD_CANDIDATE_FLOW_EPOCH",
                "time_advances": False,
                "accepted_step_advances": False,
                "grid_state_changes": False,
            },
            {
                "state": "BUILD_CANDIDATE_FLOW_EPOCH",
                "allowed_next": "FLOW_EPOCH_VALIDATION",
                "time_advances": False,
                "accepted_step_advances": False,
                "grid_state_changes": False,
            },
            {
                "state": "FLOW_EPOCH_VALIDATION",
                "allowed_next": "FLOW_EPOCH_ACTIVE or BLOCKED",
                "time_advances": False,
                "accepted_step_advances": False,
                "grid_state_changes": False,
            },
            {
                "state": "FLOW_EPOCH_ACTIVE",
                "allowed_next": "TRANSPORT_TRIAL",
                "time_advances": False,
                "accepted_step_advances": False,
                "grid_state_changes": False,
            },
            {
                "state": "TRANSPORT_TRIAL",
                "allowed_next": (
                    "ACCEPTED_TRANSITION, FLOW_REFRESH_REQUIRED, "
                    "CAPACITY_FALLBACK, or NATIVE_RETRY"
                ),
                "time_advances": False,
                "accepted_step_advances": False,
                "grid_state_changes": False,
            },
            {
                "state": "ACCEPTED_TRANSITION",
                "allowed_next": (
                    "FLOW_EPOCH_ACTIVE or FLOW_REFRESH_REQUIRED "
                    "according to trigger evaluation"
                ),
                "time_advances": True,
                "accepted_step_advances": True,
                "grid_state_changes": True,
            },
            {
                "state": "CAPACITY_FALLBACK",
                "allowed_next": "TRANSPORT_TRIAL or BLOCKED",
                "time_advances": False,
                "accepted_step_advances": False,
                "grid_state_changes": False,
            },
        ]

        cadence_rows = []
        for name, days in CADENCE_CANDIDATES_DAYS.items():
            cadence_rows.append(
                {
                    "policy": name,
                    "max_flow_epoch_days": "" if days is None else days,
                    "production_authorized": False,
                    "role": (
                        "event-driven reference"
                        if days is None
                        else "cadence-sensitivity candidate"
                    ),
                }
            )

        contract = {
            "milestone": MILESTONE,
            "status": STATUS,
            "architecture_only": True,
            "solver_execution_performed": False,
            "canonical_state_created": False,
            "physical_time_advanced": False,
            "accepted_step_index_advanced": False,
            "scientific_basis": {
                "R3R1_capacity_lock": (
                    "Persistent tiny-dt map-back capacity lock under stale flow geometry."
                ),
                "R3R2R1_result": (
                    "Recomputing saturation-dependent mobility, pressure, conservative "
                    "Darcy fluxes, Pollock streamlines, TOF, and overlap geometry removed "
                    "all nominal-step overcapacity cells."
                ),
                "interpretation": (
                    "The observed lock is treated as stale-flow-field coupling evidence, "
                    "not reservoir-wide storage exhaustion."
                ),
            },
            "two_level_time_structure": {
                "global_flow_epoch": (
                    "Pressure/velocity/streamline/TOF/overlap quantities are fixed "
                    "only inside one validated flow epoch."
                ),
                "local_transport_steps": (
                    "Conservative CV component-mass transport, exact map-back, "
                    "capillary redistribution, and closure checks advance state "
                    "inside the active flow epoch."
                ),
            },
            "refresh_pipeline": refresh_pipeline,
            "hard_refresh_triggers": [
                "RESTART_OR_INITIALIZATION",
                "WELL_OR_CONTROL_CHANGE",
                "POST_OBSERVATION_CHECKPOINT",
                "CAPACITY_PREFLIGHT_REJECTION",
            ],
            "capacity_trigger_semantics": {
                "first_response": (
                    "Rollback/reject the uncommitted trial and refresh the full flow "
                    "epoch from the exact same accepted parent state."
                ),
                "same_parent_retry_dt": (
                    "Retry the same candidate transport dt after the refreshed flow "
                    "epoch is validated; do not halve dt before this refresh attempt."
                ),
                "repeat_refresh_same_parent": False,
                "post_refresh_if_still_capacity_unsafe": (
                    "Use the existing conservative R2 capacity-aware timestep controller "
                    "for that transition only; no clipping, rescaling, support expansion, "
                    "or capillary modification is authorized."
                ),
                "after_capacity_limited_acceptance": (
                    "Force FLOW_REFRESH_REQUIRED before any subsequent transport transition."
                ),
            },
            "rollback_semantics": {
                "refresh_is_not_a_physical_transition": True,
                "refresh_does_not_advance_time": True,
                "refresh_does_not_increment_accepted_step": True,
                "refresh_does_not_change_grid_inventory": True,
                "failed_flow_epoch_never_becomes_active": True,
            },
            "flow_epoch_frozen_quantities": [
                "pressure_psi",
                "Qx_m3_s",
                "Qy_m3_s",
                "Qz_m3_s",
                "Pollock_streamline_geometry",
                "streamline_weights",
                "TOF_coordinates",
                "SG7D_subsegment_overlap",
                "E37A_control_volume_geometry",
                "streamline_face_pressure",
            ],
            "flow_epoch_mutable_quantities": [
                "Cartesian_transport_saturation",
                "Cartesian_component_mass",
                "CV_component_mass_for_each_local_trial",
                "capillary_redistributed_grid_state",
                "cumulative_injection_production_storage_ledgers",
                "breakthrough_and_observation_metadata",
            ],
            "calibration_policy": {
                "production_cadence_not_yet_frozen": True,
                "observed_stale_interval_days": OBSERVED_STALE_INTERVAL_DAYS,
                "candidate_max_epoch_days": CADENCE_CANDIDATES_DAYS,
                "derivation": (
                    "Geometric refinement of the observed 60 d -> 69.883467 d "
                    "stale-flow interval; no arbitrary absolute day interval is promoted "
                    "directly to production."
                ),
                "future_selection_requires": [
                    "conservation closure",
                    "pressure/velocity sensitivity",
                    "producer gas-cut sensitivity",
                    "stored CO2 mass sensitivity",
                    "plume-support sensitivity",
                    "refresh-count / runtime cost",
                ],
            },
            "next_controlled_milestone": {
                "name": NEXT,
                "objective": (
                    "At the exact R3-R1 parent, build the R3-R2-R1 saturation-updated "
                    "flow epoch and execute one same-parent nominal transport transition. "
                    "Prove that the nominal transition is admissible without the stale-flow "
                    "capacity collapse and that all component-mass/capillary closures pass."
                ),
                "long_horizon_100d_not_authorized_yet": True,
            },
            "no_go": [
                "Do not raise the Sg=0.60 incremental saturation ceiling.",
                "Do not clip, delete, or globally rescale component mass.",
                "Do not invent new spatial support during map-back.",
                "Do not modify the capillary solver in response to the stale-flow diagnosis.",
                "Do not increase transition budgets as a substitute for flow refresh.",
                "Do not refresh pressure/streamlines by mutating an accepted grid state.",
                "Do not promote a cadence candidate to production before sensitivity calibration.",
            ],
            "next_milestone": NEXT,
        }

        gate(
            "contract_capacity_refresh_before_dt_reduction",
            contract["capacity_trigger_semantics"]["same_parent_retry_dt"].startswith(
                "Retry the same candidate"
            ),
        )
        gate(
            "contract_no_repeat_same_parent_refresh",
            contract["capacity_trigger_semantics"]["repeat_refresh_same_parent"] is False,
        )
        gate(
            "contract_refresh_has_no_state_advance",
            all(
                contract["rollback_semantics"][k] is True
                for k in [
                    "refresh_is_not_a_physical_transition",
                    "refresh_does_not_advance_time",
                    "refresh_does_not_increment_accepted_step",
                    "refresh_does_not_change_grid_inventory",
                ]
            ),
        )
        gate(
            "contract_long_horizon_not_authorized",
            contract["next_controlled_milestone"]["long_horizon_100d_not_authorized_yet"]
            is True,
        )
        gate(
            "contract_cadence_requires_calibration",
            contract["calibration_policy"]["production_cadence_not_yet_frozen"] is True,
        )

        closure_out = {
            "milestone": MILESTONE,
            "status": STATUS,
            "all_gates_passed": all(v["passed"] for v in gates.values()),
            "gate_count": len(gates),
            "architecture_only": True,
            "solver_execution_performed": False,
            "canonical_state_created": False,
            "physical_time_advanced": False,
            "production_cadence_frozen": False,
            "capacity_event_refresh_semantics_frozen": True,
            "next_milestone": NEXT,
        }

        files = {
            "PAD_Stream_V16E41R3R3_Architecture_Contract.json": json_bytes(contract),
            "V16E41R3R3_Flow_Refresh_Pipeline.csv": csv_bytes(refresh_pipeline),
            "V16E41R3R3_Refresh_Trigger_Priority.csv": csv_bytes(trigger_rows),
            "V16E41R3R3_Runtime_State_Machine.csv": csv_bytes(state_machine_rows),
            "V16E41R3R3_Cadence_Sensitivity_Candidates.csv": csv_bytes(cadence_rows),
            "V16E41R3R3_Final_Gate_Matrix.csv": csv_bytes(
                [{"gate": k, **v} for k, v in gates.items()]
            ),
            "V16E41R3R3_Final_Closure.json": json_bytes(closure_out),
        }

        immutable_publish(out, files)

        manifest = []
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name != "V16E41R3R3_Artifact_Manifest.csv":
                manifest.append(
                    {
                        "file": p.name,
                        "sha256": sha256_file(p),
                        "bytes": p.stat().st_size,
                    }
                )
        immutable_publish(
            out,
            {"V16E41R3R3_Artifact_Manifest.csv": csv_bytes(manifest)},
        )

        print("\n" + "=" * 154)
        print("PAD-Stream V16E-41-R3-R3: PASS")
        print("=" * 154)
        print(f"{'Status':64}: {STATUS}")
        print(
            f"{'R3-R2-R1 diagnosis':64}: "
            f"{summary.get('diagnosis')}"
        )
        print(
            f"{'Frozen -> updated overcapacity cells':64}: "
            f"{frozen_cap.get('overcapacity_cell_count')} -> "
            f"{updated_cap.get('overcapacity_cell_count')}"
        )
        print(
            f"{'Pressure relative L2 change at diagnosis':64}: "
            f"{summary.get('updated_pressure_relative_L2_vs_frozen')}"
        )
        print(
            f"{'Observed stale-flow interval':64}: "
            f"{OBSERVED_STALE_INTERVAL_DAYS:.15g} d"
        )
        print(
            f"{'Cadence candidates (days)':64}: "
            f"{CADENCE_CANDIDATES_DAYS}"
        )
        print(
            f"{'Capacity event first response':64}: "
            "same-parent full flow refresh before dt reduction"
        )
        print(
            f"{'100-day production rollout authorized':64}: False"
        )
        print(f"{'Output':64}: {out}")
        print(f"{'Next':64}: {NEXT}")
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": MILESTONE,
            "status": "SATURATION_UPDATED_FLOW_REFRESH_RUNTIME_ARCHITECTURE_FREEZE_BLOCKED",
            "failed_stage": failed_stage,
            "exception": repr(exc),
            "gates": gates,
        }
        data = json_bytes(report)
        p = blocked / "V16E41R3R3_Blocked_Architecture_Freeze.json"
        if p.exists() and p.read_bytes() != data:
            p = blocked / (
                "V16E41R3R3_Blocked_Architecture_Freeze_"
                + hashlib.sha256(data).hexdigest()[:12]
                + ".json"
            )
        p.write_bytes(data)

        print("\n" + "=" * 154)
        print("PAD-Stream V16E-41-R3-R3: BLOCKED")
        print("=" * 154)
        print("Report      :", p)
        print("Failed stage:", failed_stage)
        print("Exception   :", repr(exc))
        return 2


def parse_args() -> argparse.Namespace:
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
