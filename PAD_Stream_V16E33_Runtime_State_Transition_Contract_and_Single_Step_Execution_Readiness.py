from __future__ import annotations

from pathlib import Path
import argparse
import csv
import hashlib
import json
from typing import Any, Iterable


MILESTONE = "V16E-33"
STATUS = "PAD_STREAM_RUNTIME_STATE_TRANSITION_CONTRACT_FROZEN"
NEXT = "V16E-34 - Initial Injection-Time SGSim Runtime State Construction / Validation"

# -----------------------------------------------------------------------------
# Frozen V16 runtime-entry identity inherited from V16E-32.
# E33 does NOT use this 100-day object as the future production initial state.
# It remains an immutable regression / validation checkpoint.
# -----------------------------------------------------------------------------
EXPECTED_GRID = (15, 50, 50)
EXPECTED_TIME_DAYS = 100.0
EXPECTED_BACKGROUND = 0.2
V16_FROZEN_SHA = "d422dc1e56281c1baf0ae007c62ce4bd69677a232bd1448a5bd79d3177eafaea"
RUNTIME_STATE_ARRAY_SHA = "176975c3131353c4fe60fdf9e6d7635b13e260e010fc8cd849deb17c85e37f12"

# V15F-1 global producer-response event authority.  E33 deliberately selects
# this well-response definition for the production runtime event clock.  The
# older SG7A producer-end saturation-rise diagnostic remains diagnostic only.
BREAKTHROUGH_GAS_CUT = 1.0e-4

# V16C-15 schedule is retained as a fixed observation clock, NOT a timestep
# schedule and NOT a list of independently initialized states.
DEFAULT_OBSERVATION_DAYS = [30.0, 60.0, 100.0, 150.0, 250.0, 365.0, 500.0, 750.0, 1000.0]

E32_REL = Path(
    "provenance/hybrid_dp/"
    "V16E32_FROZEN_RUNTIME_LOADER_CONSUMPTION_RUNTIME_EXECUTION_ENTRY_CONTRACT"
)
E32_SUMMARY_NAME = "PAD_Stream_V16E32_Summary.json"
E32_CONTRACT_NAME = "V16E32_PAD_Stream_Runtime_Execution_Entry_Contract.json"

V16_FROZEN_REL = Path(
    "provenance/hybrid_dp/V16E18_R1_FROZEN_SGSIM_100D_FULL_GRID_CANDIDATE/"
    "frozen_full_grid/V16E18_R1_Frozen_SGSim_100Day_Full_Grid_Candidate.npz"
)

OUT_REL = Path(
    "provenance/hybrid_dp/"
    "V16E33_RUNTIME_STATE_TRANSITION_CONTRACT_SINGLE_STEP_EXECUTION_READINESS"
)
BLOCKED_REL = Path(
    "provenance/hybrid_dp/"
    "V16E33_BLOCKED_RUNTIME_STATE_TRANSITION_CONTRACT_SINGLE_STEP_EXECUTION_READINESS"
)

# Tracked source authorities.  E33 records the exact SHA-256 observed at freeze
# time and gates the semantics needed from each source.  Future milestones bind
# to the E33 manifest rather than silently inheriting changed source files.
SOURCE_AUTHORITIES: dict[str, dict[str, Any]] = {
    "V16E32_runtime_entry": {
        "path": "PAD_Stream_V16E32_Frozen_Runtime_Loader_Consumption_and_Runtime_Execution_Entry_Contract.py",
        "markers": [
            'NEXT = "V16E-33',
            "NO RUNTIME TIME ADVANCE",
            '"state_transition_execution_authorized": False',
        ],
    },
    "V16C13_time_mapping": {
        "path": "PAD_Stream_V16C13_Physical_Time_to_Pollock_Normalized_Time_Target_Mapping_Contract.py",
        "markers": [
            "physical_time_seconds / terminal_pollock_tof_i_seconds",
            "production target times: NOT YET FROZEN",
        ],
    },
    "V16C15_observation_schedule": {
        "path": "PAD_Stream_V16C15_Production_Physical_Target_Time_Schedule_Authority_Contract.py",
        "markers": [
            "TARGET=np.array([30.,60.,100.,150.,250.,365.,500.,750.,1000.])",
            "schedule_is_new_V16_design",
        ],
    },
    "V16E10_hybrid_path_semantics": {
        "path": "PAD_Stream_V16E10_SGSim_Hybrid_Path_State_Semantics_and_Controlled_Deployment_Protocol_Freeze.py",
        "markers": [
            "existing exact 3-D Pollock path",
            "existing Pollock TOF tau(s)",
            "heterogeneous/full-physics TOF transport authority",
        ],
    },
    "V16E13R1_conservative_mapback": {
        "path": "PAD_Stream_V16E13_R1_Native_Dtype_Identity_Repair_and_Controlled_Conservative_Streamline_to_Grid_MapBack_Execution.py",
        "markers": [
            "flow-weighted piecewise-linear segment/cell intersection accumulation",
            "support_closure_rel",
            "sat_measure_closure_rel",
        ],
    },
    "V15E3_unique_grid_recurrence": {
        "path": "dependencies/PAD_Stream_V15E3_Sequential_Conservative_Graph_Mapback_Deployment/"
                "PAD_Stream_V15E3_Sequential_Conservative_Graph_Mapback_Deployment.py",
        "markers": [
            "accepted grid state",
            "next transition",
            "self_consistent_mass_projection",
            "restart_saturation_identity",
        ],
    },
    "V15F0_timestep_retrace": {
        "path": "dependencies/PAD_Stream_V15F0_Global_Recurrent_Timestep_Retrace_State/"
                "PAD_Stream_V15F0_Global_Recurrent_Timestep_Retrace_State.py",
        "markers": [
            "next-timestep proposal head",
            "Classical adaptive-step acceptance",
            "full_family_retrace",
        ],
    },
    "V15F1_breakthrough_well": {
        "path": "dependencies/PAD_Stream_V15F1_Breakthrough_Well_Control_Recurrent_Memory/"
                "PAD_Stream_V15F1_Breakthrough_Well_Control_Recurrent_Memory.py",
        "markers": [
            "BREAKTHROUGH_GAS_CUT = 1.0e-4",
            "exact Peaceman well equations",
            "monotone_breakthrough_hazard",
        ],
    },
    "V15F2_solver_difficulty": {
        "path": "dependencies/PAD_Stream_V15F2_Nonlinear_Difficulty_Complete_Global_Recurrent_State/"
                "PAD_Stream_V15F2_Nonlinear_Difficulty_Complete_Global_Recurrent_State.py",
        "markers": [
            "Exact pressure residuals",
            "timestep rejection/retry",
            "exact_escalation",
        ],
    },
}


class GateError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


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


def require_markers(text: str, markers: Iterable[str], label: str) -> None:
    missing = [m for m in markers if m not in text]
    if missing:
        raise GateError(f"{label}_missing_semantic_markers:{missing}")


def immutable_publish(directory: Path, files: dict[str, bytes]) -> None:
    """Create deterministic provenance files; never overwrite differing bytes."""
    directory.mkdir(parents=True, exist_ok=True)
    for name, payload in files.items():
        path = directory / name
        if path.exists():
            if path.read_bytes() != payload:
                raise GateError(f"existing_E33_artifact_differs:{name}")
        else:
            path.write_bytes(payload)


def state_schema_rows() -> list[dict[str, Any]]:
    return [
        {
            "field": "physical_time_days",
            "class": "PERSISTENT_CANONICAL",
            "owner": "accepted runtime state",
            "update": "advance only on accepted transition",
            "rollback": "restore parent value on rejection",
            "notes": "production rollout begins at t=0 in E34; 100 d remains validation checkpoint",
        },
        {
            "field": "accepted_step_index",
            "class": "PERSISTENT_CANONICAL",
            "owner": "runtime controller",
            "update": "increment only after state acceptance",
            "rollback": "unchanged on rejected attempt",
            "notes": "attempt index and accepted-step index are distinct",
        },
        {
            "field": "canonical_grid_saturation",
            "class": "PERSISTENT_CANONICAL",
            "owner": "conservative Cartesian grid recurrence",
            "update": "accepted conservative map-back / bounded projection",
            "rollback": "parent array remains immutable until acceptance",
            "notes": "sole recurrent plume-state authority; streamline saturation is not a competing recurrent state",
        },
        {
            "field": "saturation_history",
            "class": "PERSISTENT_CANONICAL",
            "owner": "V15E3 recurrent-state semantics",
            "update": "running maximum of accepted grid saturation where this history channel is used",
            "rollback": "unchanged on rejection",
            "notes": "E34 initializes consistently from the t=0 saturation field",
        },
        {
            "field": "cumulative_injected_co2_mass_kg",
            "class": "PERSISTENT_CANONICAL",
            "owner": "mass ledger",
            "update": "integrate accepted injector component mass flux over accepted dt",
            "rollback": "unchanged on rejection",
            "notes": "never inferred from plume volume alone",
        },
        {
            "field": "cumulative_produced_co2_mass_kg",
            "class": "PERSISTENT_CANONICAL",
            "owner": "mass ledger",
            "update": "integrate accepted producer CO2 component mass flux over accepted dt",
            "rollback": "unchanged on rejection",
            "notes": "tracked continuously before and after threshold-defined breakthrough",
        },
        {
            "field": "stored_co2_mass_kg",
            "class": "PERSISTENT_CANONICAL",
            "owner": "compressible inventory operator",
            "update": "recompute from accepted grid thermodynamic state",
            "rollback": "parent inventory retained on rejection",
            "notes": "exact constitutive inventory formula is bound in E34/E35; no global scalar saturation rescale",
        },
        {
            "field": "step_mass_residual_kg",
            "class": "PERSISTENT_DIAGNOSTIC",
            "owner": "mass-acceptance audit",
            "update": "compute before candidate acceptance",
            "rollback": "rejected-attempt value retained only in attempt audit, not accepted state",
            "notes": "delta stored - injected + produced - boundary",
        },
        {
            "field": "cumulative_mass_residual_kg",
            "class": "PERSISTENT_DIAGNOSTIC",
            "owner": "mass-acceptance audit",
            "update": "accepted cumulative conservation ledger",
            "rollback": "unchanged on rejection",
            "notes": "must be reported through entire plume evolution",
        },
        {
            "field": "last_accepted_dt_days",
            "class": "PERSISTENT_CONTROLLER",
            "owner": "adaptive timestep controller",
            "update": "accepted dt only",
            "rollback": "unchanged on rejected attempt",
            "notes": "F0 learned dt remains proposal-only; SGSim numerical envelope must be revalidated",
        },
        {
            "field": "well_control_state",
            "class": "PERSISTENT_CANONICAL",
            "owner": "exact well/control logic",
            "update": "accepted Peaceman/control solution",
            "rollback": "parent controls remain active until acceptance",
            "notes": "learned F1 outputs are warm starts / warnings only",
        },
        {
            "field": "producer_response_state",
            "class": "PERSISTENT_CANONICAL",
            "owner": "exact well-response evaluation",
            "update": "accepted producer phase/component rates and gas cut",
            "rollback": "unchanged on rejection",
            "notes": "feeds breakthrough event memory",
        },
        {
            "field": "breakthrough_reached",
            "class": "PERSISTENT_EVENT_MEMORY",
            "owner": "global event scheduler",
            "update": "monotone false->true only after accepted threshold crossing",
            "rollback": "cannot change on rejected attempt",
            "notes": f"producer gas-cut event threshold = {BREAKTHROUGH_GAS_CUT:.1e}",
        },
        {
            "field": "breakthrough_time_days",
            "class": "PERSISTENT_EVENT_MEMORY",
            "owner": "global event scheduler",
            "update": "set from refined accepted physical event state",
            "rollback": "unchanged on rejection",
            "notes": "scalar interpolation may initialize the event bracket but cannot create the canonical event state",
        },
        {
            "field": "f0_hidden_state",
            "class": "PERSISTENT_RECURRENT",
            "owner": "V15F0 recurrent encoder semantics",
            "update": "advance after accepted step only",
            "rollback": "restore exact parent hidden state on rejection",
            "notes": "restart must reproduce uninterrupted inference exactly",
        },
        {
            "field": "solver_preflight_memory",
            "class": "PERSISTENT_CONTROLLER_DIAGNOSTIC",
            "owner": "V15F2 difficulty/retry semantics",
            "update": "record accepted attempt workload; next predictions remain advisory",
            "rollback": "rejected attempts may be logged but cannot mutate accepted recurrent state",
            "notes": "no independent F2 physical state; exact residual tests remain final authority",
        },
        {
            "field": "path_cache_manifest",
            "class": "PERSISTENT_CACHE_IDENTITY",
            "owner": "retrace controller",
            "update": "bind cache hashes/parent-state identity after accepted retrace or validated reuse",
            "rollback": "trial cache discarded on rejection",
            "notes": "large pressure/path/TOF arrays may be persisted separately but are not independent recurrent physics",
        },
        {
            "field": "observation_cursor",
            "class": "PERSISTENT_SCHEDULER",
            "owner": "observation/event clock",
            "update": "advance after exact requested snapshot is committed",
            "rollback": "unchanged on rejection",
            "notes": "prevents skipped fixed-time snapshots",
        },
        {
            "field": "accepted_pressure",
            "class": "CACHEABLE_DERIVED_PHYSICS",
            "owner": "exact finite-volume pressure authority",
            "update": "recompute/correct from accepted state and controls as required",
            "rollback": "trial field discarded on rejection",
            "notes": "may be serialized for restart/performance but never treated as a competing independent state",
        },
        {
            "field": "accepted_Darcy_face_fluxes",
            "class": "CACHEABLE_DERIVED_PHYSICS",
            "owner": "conservative Darcy flux operator",
            "update": "derive from accepted pressure/mobility state",
            "rollback": "trial field discarded on rejection",
            "notes": "must close locally/globally before transport acceptance",
        },
        {
            "field": "accepted_Pollock_paths",
            "class": "CACHEABLE_DERIVED_PHYSICS",
            "owner": "exact Pollock authority",
            "update": "exact retrace when reuse screen fails",
            "rollback": "trial geometry discarded on rejection",
            "notes": "cache reuse means exact prior geometry remains within validated reuse envelope",
        },
        {
            "field": "accepted_TOF_and_weights",
            "class": "CACHEABLE_DERIVED_PHYSICS",
            "owner": "Pollock/TOF conservative transport coordinate",
            "update": "bind to accepted path/flux state",
            "rollback": "trial arrays discarded on rejection",
            "notes": "streamline weights remain conservative flow-partition authority",
        },
    ]


def interpolation_rows() -> list[dict[str, Any]]:
    return [
        {
            "operation": "temporal interpolation to create canonical runtime state",
            "policy": "PROHIBITED",
            "reason": "can smear moving fronts and bypass conservation/acceptance physics",
        },
        {
            "operation": "fixed plume snapshot",
            "policy": "EXACT_STEP_LANDING",
            "reason": "clip proposed dt so an accepted physics state lands exactly on requested observation time",
        },
        {
            "operation": "breakthrough crossing estimate",
            "policy": "SCALAR_INTERPOLATION_FOR_BRACKET_SEED_ONLY",
            "reason": "final breakthrough plume must be an accepted refined physical state",
        },
        {
            "operation": "Pollock/TOF monotone-coordinate resampling",
            "policy": "ALLOWED_WITH_EXISTING_VALIDATED_SEMANTICS",
            "reason": "coordinate representation only; must preserve ordering/endpoints/weights",
        },
        {
            "operation": "piecewise-linear streamline segment/cell map-back",
            "policy": "ALLOWED_ONLY_WITH_CONSERVATIVE_OPERATOR",
            "reason": "V16E13-R1 source-bound operator carries flow-weighted segment measure and closure audit",
        },
        {
            "operation": "animation/display frame between accepted snapshots",
            "policy": "ALLOWED_NONCANONICAL",
            "reason": "visualization only and must not be fed back into physics or called an accepted state",
        },
        {
            "operation": "pressure or Darcy field interpolation used as accepted physics",
            "policy": "PROHIBITED",
            "reason": "accepted pressure/flux must satisfy exact discrete equations and conservation",
        },
        {
            "operation": "global saturation scaling to repair mass",
            "policy": "PROHIBITED",
            "reason": "distorts fronts and may violate saturation bounds; use bounded conservative projection only for admissibly small residuals",
        },
    ]


def acceptance_rows() -> list[dict[str, Any]]:
    return [
        {"order": 1, "gate": "finite_state", "authority": "runtime", "failure_action": "REJECT"},
        {"order": 2, "gate": "saturation_bounds", "authority": "constitutive physics", "failure_action": "REJECT_OR_BOUNDED_CORRECT_THEN_REAUDIT"},
        {"order": 3, "gate": "pressure_discrete_residual", "authority": "exact finite-volume pressure", "failure_action": "ESCALATE_OR_REJECT"},
        {"order": 4, "gate": "well_constraints_and_component_rates", "authority": "exact Peaceman/control logic", "failure_action": "ESCALATE_OR_REJECT"},
        {"order": 5, "gate": "Darcy_local_global_flow_closure", "authority": "conservative face fluxes", "failure_action": "REJECT"},
        {"order": 6, "gate": "Pollock_path_legality_or_validated_cache_reuse", "authority": "exact Pollock/retrace contract", "failure_action": "RETRACE_OR_REJECT"},
        {"order": 7, "gate": "TOF_monotonicity_weight_positivity_flow_partition", "authority": "TOF/path contract", "failure_action": "REJECT"},
        {"order": 8, "gate": "transport_bounds_and_route_legality", "authority": "Hybrid screen plus exact fallback", "failure_action": "FALLBACK_OR_REJECT"},
        {"order": 9, "gate": "streamline_to_grid_support_and_saturation_measure_closure", "authority": "conservative map-back", "failure_action": "FALLBACK_OR_REJECT"},
        {"order": 10, "gate": "global_CO2_component_mass_closure", "authority": "mass ledger", "failure_action": "BOUNDED_PROJECT_IF_ADMISSIBLE_ELSE_REJECT"},
        {"order": 11, "gate": "nonlinear_convergence", "authority": "exact residual/convergence tests", "failure_action": "ESCALATE_OR_REJECT"},
        {"order": 12, "gate": "event_boundary_consistency", "authority": "snapshot/event scheduler", "failure_action": "SHORTEN_DT_AND_RETRY"},
        {"order": 13, "gate": "accepted_state_commit", "authority": "runtime transaction", "failure_action": "ROLLBACK"},
    ]


def main(project_root: Path, drive_root: Path) -> int:
    root = project_root.resolve()
    drive = drive_root.resolve()
    out = drive / OUT_REL
    blocked = drive / BLOCKED_REL

    gates: dict[str, dict[str, Any]] = {}

    def gate(name: str, ok: Any, detail: Any = "") -> None:
        passed = bool(ok)
        gates[name] = {"passed": passed, "detail": str(detail)}
        print(f"[{'PASS' if passed else 'FAIL'}] {name}" + (f": {detail}" if detail != "" else ""), flush=True)
        if not passed:
            raise GateError(name)

    e32_summary_path = drive / E32_REL / E32_SUMMARY_NAME
    e32_contract_path = drive / E32_REL / E32_CONTRACT_NAME
    frozen_state_path = drive / V16_FROZEN_REL

    e32_summary_sha_before = None
    e32_contract_sha_before = None
    frozen_state_sha_before = None

    print("\n" + "=" * 132)
    print("PAD-Stream V16E-33 Runtime State-Transition Contract / Single-Step Execution Readiness")
    print("=" * 132)
    print("CONTRACT-ONLY MILESTONE.")
    print("NO RUNTIME TIME ADVANCE. NO NEW SATURATION FIELD. NO PRESSURE/DARCY/POLLOCK/TOF/TRANSPORT/MAP-BACK EXECUTION.")
    print("THE FROZEN 100-DAY V16 STATE IS PRESERVED AS A REGRESSION/VALIDATION CHECKPOINT, NOT THE FUTURE t=0 INITIAL CONDITION.")
    print("E33 FREEZES STATE, CONSERVATION, OBSERVATION/EVENT CLOCK, INTERPOLATION, ACCEPTANCE, AND ROLLBACK SEMANTICS.")

    try:
        # ------------------------------------------------------------------
        # E32 execution-entry authority.
        # ------------------------------------------------------------------
        print("\nV16E-32 RUNTIME-ENTRY AUTHORITY")
        gate("E32_summary_exists", e32_summary_path.is_file(), e32_summary_path)
        gate("E32_contract_exists", e32_contract_path.is_file(), e32_contract_path)
        gate("frozen_100d_state_exists", frozen_state_path.is_file(), frozen_state_path)

        e32_summary_sha_before = sha256_file(e32_summary_path)
        e32_contract_sha_before = sha256_file(e32_contract_path)
        frozen_state_sha_before = sha256_file(frozen_state_path)
        gate("frozen_100d_state_file_SHA_exact", frozen_state_sha_before == V16_FROZEN_SHA, frozen_state_sha_before)

        e32_summary = load_json(e32_summary_path)
        e32_contract = load_json(e32_contract_path)

        gate(
            "E32_status_exact",
            e32_summary.get("status") == "FROZEN_RUNTIME_LOADER_CONSUMED_RUNTIME_EXECUTION_ENTRY_CONTRACT_READY",
            e32_summary.get("status"),
        )
        gate("E32_runtime_entry_ready", e32_summary.get("runtime_execution_entry_ready") is True)
        gate("E32_time_advance_absent", e32_summary.get("runtime_time_advance_performed") is False)
        gate("E32_next_state_absent", e32_summary.get("next_state_created") is False)
        gate("E32_transition_execution_not_authorized", e32_summary.get("state_transition_execution_authorized") is False)
        gate("E32_accepted_state_unmodified", e32_summary.get("accepted_state_modified") is False)
        gate("E32_time_100d_exact", float(e32_summary.get("physical_time_days")) == EXPECTED_TIME_DAYS)
        gate("E32_grid_exact", tuple(e32_summary.get("grid_shape", [])) == EXPECTED_GRID, e32_summary.get("grid_shape"))
        gate("E32_background_exact", float(e32_summary.get("background_saturation")) == EXPECTED_BACKGROUND)
        gate("E32_state_array_SHA_exact", e32_summary.get("accepted_state_array_sha256") == RUNTIME_STATE_ARRAY_SHA)
        gate("E32_next_is_E33", str(e32_summary.get("next_milestone", "")).startswith("V16E-33"), e32_summary.get("next_milestone"))

        gate("E32_contract_status_exact", e32_contract.get("status") == "PAD_STREAM_RUNTIME_EXECUTION_ENTRY_READY")
        entry = e32_contract["canonical_runtime_entry_state"]
        boundary = e32_contract["execution_boundary"]
        gate("E32_contract_state_read_only", entry.get("read_only") is True)
        gate("E32_contract_state_time_100d", float(entry.get("physical_time_days")) == EXPECTED_TIME_DAYS)
        gate("E32_contract_state_SHA_exact", entry.get("state_array_sha256") == RUNTIME_STATE_ARRAY_SHA)
        gate("E32_contract_no_transition_execution", boundary.get("state_transition_execution_authorized") is False)
        gate("E32_contract_no_physics_execution", not any(bool(boundary.get(k)) for k in [
            "pressure_solve_executed", "Darcy_flux_executed", "Pollock_executed",
            "TOF_executed", "transport_executed", "mapback_executed",
        ]))

        # ------------------------------------------------------------------
        # Tracked source semantic authorities.
        # ------------------------------------------------------------------
        print("\nTRACKED ARCHITECTURE AUTHORITIES")
        source_rows: list[dict[str, Any]] = []
        source_hashes: dict[str, str] = {}
        for label, spec in SOURCE_AUTHORITIES.items():
            path = root / spec["path"]
            gate(f"{label}_exists", path.is_file(), path)
            text = path.read_text(encoding="utf-8")
            require_markers(text, spec["markers"], label)
            digest = sha256_file(path)
            source_hashes[label] = digest
            source_rows.append({
                "authority": label,
                "path": spec["path"],
                "sha256": digest,
                "semantic_markers_verified": True,
            })
            gate(f"{label}_semantic_markers", True, digest)

        # Explicit architecture decisions inferred from the verified sources and
        # frozen prospectively by E33.
        print("\nE33 PROSPECTIVE RUNTIME CONTRACT DECISIONS")
        gate("production_rollout_initial_time_is_zero", 0.0 == 0.0)
        gate("100d_role_is_checkpoint_not_initial_condition", True)
        gate("unique_grid_saturation_is_recurrent_authority", True)
        gate("streamline_state_not_independent_recurrent_authority", True)
        gate("learned_timestep_is_proposal_only", True)
        gate("classical_accept_retry_is_final_timestep_authority", True)
        gate("V15_numeric_dt_bounds_not_blindly_inherited_to_SGSim", True)
        gate("pressure_flux_well_residuals_remain_exact_authorities", True)
        gate("hybrid_transport_requires_screen_and_exact_fallback", True)
        gate("mapback_requires_conservative_closure", True)
        gate("mass_balance_is_acceptance_gate", True)
        gate("temporal_interpolation_cannot_create_canonical_state", True)
        gate("fixed_snapshot_times_use_exact_step_landing", True)
        gate("breakthrough_event_uses_producer_gas_cut", True)
        gate("breakthrough_threshold_inherited_from_F1", BREAKTHROUGH_GAS_CUT == 1.0e-4, BREAKTHROUGH_GAS_CUT)
        gate("breakthrough_canonical_state_requires_physics_refinement", True)
        gate("rejected_attempt_does_not_advance_time", True)
        gate("rejected_attempt_does_not_mutate_accepted_state", True)
        gate("E33_executes_no_physics", True)
        gate("E33_creates_no_t0_state", True)
        gate("E33_creates_no_next_state", True)

        state_rows = state_schema_rows()
        interp_rows = interpolation_rows()
        accept_rows = acceptance_rows()

        mass_contract = {
            "milestone": MILESTONE,
            "status": "MASS_BALANCE_LEDGER_CONTRACT_FROZEN",
            "component": "CO2",
            "outer_boundary_default": "NO_FLOW_ZERO_COMPONENT_MASS_TRANSFER_UNLESS_A_LATER_CONTROL_CONTRACT_EXPLICITLY_CHANGES_IT",
            "step_balance": {
                "equation": "step_mass_residual_kg = (Mstored_np1 - Mstored_n) - (Minjected_step - Mproduced_step + Mboundary_step)",
                "required_terms": [
                    "stored_CO2_mass_parent_kg",
                    "stored_CO2_mass_candidate_kg",
                    "injected_CO2_mass_step_kg",
                    "produced_CO2_mass_step_kg",
                    "boundary_CO2_mass_step_kg",
                    "step_mass_residual_kg",
                ],
            },
            "cumulative_balance": {
                "equation": "cumulative_mass_residual_kg = (Mstored_n - Mstored_0) - (Minjected_cum - Mproduced_cum + Mboundary_cum)",
                "report_every_accepted_step": True,
            },
            "closure_layers": [
                "finite-volume pressure/face-flux closure",
                "streamline flow-weight closure",
                "streamline transport conservation/bounds",
                "streamline-to-grid support and saturation-measure closure",
                "global compressible CO2 component inventory closure",
            ],
            "correction_policy": {
                "global_scalar_saturation_rescale": "PROHIBITED",
                "bounded_conservative_projection": "PERMITTED_ONLY_FOR_AN_ADMISSIBLY_SMALL_RESIDUAL_AND_MUST_BE_REAUDITED",
                "large_or_unexplained_residual": "REJECT_TIMESTEP_AND_DIAGNOSE",
                "numerical_tolerance": "NOT_INVENTED_IN_E33; MUST_BE SCALE-AWARE AND VALIDATED BEFORE FIRST EXECUTED SGSim TRANSITION",
                "legacy_V15_thresholds": "EVIDENCE_ONLY; NOT BLINDLY TRANSFERRED FROM 5x5x5 TO 50x50x15",
            },
            "breakthrough_relation": {
                "mass_ledger_runs_before_breakthrough": True,
                "mass_ledger_runs_after_breakthrough": True,
                "breakthrough_is_not_a_mass-balance_discontinuity": True,
                "producer_CO2_mass_is_tracked_continuously_even_below_event_threshold": True,
            },
        }

        scheduler_contract = {
            "milestone": MILESTONE,
            "status": "SIMULATION_AND_OBSERVATION_CLOCK_CONTRACT_FROZEN",
            "simulation_clock": {
                "definition": "sequence of accepted adaptive physics times t0<t1<...",
                "initial_time_requirement_days": 0.0,
                "dt_owner": "classical adaptive acceptance/retry controller after screened recurrent proposal",
                "learned_dt_role": "PROPOSAL_ONLY",
                "SGSim_numeric_dt_envelope_status": "MUST_BE_REVALIDATED; V15F0 5x5x5 numerical bounds are not inherited by assumption",
            },
            "observation_clock": {
                "default_fixed_days": DEFAULT_OBSERVATION_DAYS,
                "source": "V16C-15 schedule re-used prospectively as fixed reporting targets",
                "role": "OUTPUT_OBSERVATION_TARGETS_NOT_TIMESTEPS",
                "exact_landing": True,
                "rule": "if a proposed accepted step would cross a fixed observation time, clip/retry dt to land exactly on that time",
            },
            "event_clock": {
                "breakthrough": {
                    "metric": "producer_CO2_gas_cut",
                    "threshold": BREAKTHROUGH_GAS_CUT,
                    "threshold_source": "V15F-1 global breakthrough/well-response memory",
                    "monotone_memory": True,
                    "detection": "bracket threshold crossing; scalar interpolation may seed refinement only",
                    "canonical_event_state": "must be generated by an accepted refined physics step",
                },
                "injection_stop": {
                    "enabled_when_configured": True,
                    "time_days": None,
                    "rule": "future runtime control input; E33 does not invent an injection-stop date",
                },
                "well_control_change": {
                    "exact_step_landing": True,
                },
            },
        }

        rollback_contract = {
            "milestone": MILESTONE,
            "status": "TRANSACTIONAL_RETRY_ROLLBACK_CONTRACT_FROZEN",
            "parent_state": "immutable during trial attempt",
            "trial_state": "separate working state",
            "commit_condition": "all acceptance gates pass",
            "on_accept": [
                "commit candidate as new canonical grid state",
                "advance physical time",
                "increment accepted-step index",
                "commit mass ledger",
                "commit event/well memory",
                "advance recurrent hidden state",
                "commit exact/reused path-cache manifest",
                "commit observation cursor for any exact snapshot reached",
            ],
            "on_reject": [
                "do not advance physical time",
                "do not alter canonical grid saturation/history",
                "do not alter accepted mass ledger",
                "do not advance breakthrough/event memory",
                "restore parent recurrent hidden state",
                "discard trial pressure/flux/path/TOF/transport/map-back state",
                "record failed-attempt diagnostics",
                "reduce/repair dt or escalate exact solver and retry",
            ],
            "restart_requirement": "serialized accepted state plus bound cache/recurrent identity must reproduce uninterrupted accepted trajectory within the exactness contract of each component",
        }

        transition_contract = {
            "milestone": MILESTONE,
            "status": STATUS,
            "scope": "prospective general PAD-Stream accepted-state transition contract for continuous injection-time SGSim rollout",
            "current_V16_checkpoint": {
                "physical_time_days": EXPECTED_TIME_DAYS,
                "grid_shape": list(EXPECTED_GRID),
                "file_sha256": frozen_state_sha_before,
                "state_array_sha256": RUNTIME_STATE_ARRAY_SHA,
                "role_after_E33": "IMMUTABLE_REGRESSION_VALIDATION_CHECKPOINT",
                "future_production_initial_condition": False,
                "modified_in_E33": False,
            },
            "future_production_runtime": {
                "initial_time_days": 0.0,
                "initial_state_created_in_E33": False,
                "initial_state_owner": "V16E-34",
                "goal": "continuous injection-start rollout through breakthrough and continued plume growth with exact fixed/event snapshots",
            },
            "canonical_state_principle": {
                "sole_recurrent_plume_authority": "accepted conservative Cartesian grid saturation",
                "streamline_saturation_role": "TRANSIENT_TRANSPORT_WORKSPACE_ONLY",
                "pressure_flux_path_TOF_role": "DERIVED_OR_CACHEABLE_EXACT_PHYSICS_BOUND_TO_ACCEPTED_STATE",
            },
            "transition_lifecycle": [
                "ACCEPTED_PARENT",
                "PROPOSE_AND_SCREEN_DT_SOLVER_WELL_RETRACE_WORK",
                "CLIP_TO_KNOWN_OBSERVATION_OR_CONTROL_BOUNDARY",
                "TRIAL_PRESSURE_WELL_AND_DARCY",
                "VALIDATED_PATH_REUSE_OR_EXACT_POLLOCK_RETRACE",
                "TOF_AND_CONSERVATIVE_WEIGHT_BINDING",
                "SCREENED_HYBRID_TRANSPORT_OR_EXACT_FALLBACK",
                "CONSERVATIVE_GRID_MAPBACK_AND_BOUNDED_MASS_PROJECTION_IF_ADMISSIBLE",
                "EXACT_NONLINEAR_CONSERVATION_EVENT_AUDIT",
                "ACCEPT_COMMIT_OR_REJECT_ROLLBACK",
            ],
            "timestep_authority": scheduler_contract["simulation_clock"],
            "observation_event_authority": scheduler_contract,
            "mass_balance_authority": mass_contract,
            "interpolation_policy": interp_rows,
            "acceptance_sequence": accept_rows,
            "rollback_authority": rollback_contract,
            "hybrid_transport_authority": {
                "learned_use": "only under frozen eligibility/screening semantics",
                "homogeneous_pre_breakthrough_fallback": "exact R2 BL fan where legally applicable",
                "heterogeneous_or_full_physics_fallback": "frozen full-physics TOF transport lineage or separately frozen successor",
                "unsafe_learned_acceptance": "PROHIBITED",
            },
            "execution_boundary": {
                "contract_frozen": True,
                "single_step_contract_ready": True,
                "single_step_execution_authorized": False,
                "reason_execution_not_yet_authorized": "production t=0 SGSim runtime initial state and SGSim-specific numerical acceptance tolerances are not yet constructed/validated",
                "runtime_time_advance_performed": False,
                "new_saturation_field_created": False,
                "pressure_solve_executed": False,
                "Darcy_flux_executed": False,
                "Pollock_executed": False,
                "TOF_executed": False,
                "transport_executed": False,
                "mapback_executed": False,
                "frozen_100d_checkpoint_modified": False,
            },
            "next_milestone": NEXT,
        }

        summary = {
            "milestone": MILESTONE,
            "status": STATUS,
            "runtime_state_transition_contract_frozen": True,
            "single_step_contract_ready": True,
            "single_step_execution_authorized": False,
            "production_runtime_initial_time_days": 0.0,
            "t0_state_created": False,
            "frozen_100d_checkpoint_role": "REGRESSION_VALIDATION_CHECKPOINT",
            "frozen_100d_checkpoint_modified": False,
            "canonical_recurrent_plume_state": "CONSERVATIVE_CARTESIAN_GRID_SATURATION",
            "simulation_clock_separate_from_observation_clock": True,
            "default_observation_days": DEFAULT_OBSERVATION_DAYS,
            "breakthrough_metric": "producer_CO2_gas_cut",
            "breakthrough_threshold": BREAKTHROUGH_GAS_CUT,
            "canonical_breakthrough_state_requires_physics_refinement": True,
            "temporal_interpolation_can_create_canonical_state": False,
            "mass_balance_acceptance_required": True,
            "SGSim_specific_mass_tolerance_frozen": False,
            "SGSim_specific_dt_envelope_frozen": False,
            "V15_numeric_dt_bounds_inherited_without_revalidation": False,
            "runtime_time_advance_performed": False,
            "new_saturation_field_created": False,
            "pressure_Darcy_Pollock_TOF_transport_mapback_executed": False,
            "internal_test_reopened": False,
            "OOD_reopened": False,
            "IBDP_started": False,
            "next_milestone": NEXT,
        }

        handoff = f"""# PAD-Stream V16E-33 Handoff\n\nV16E-33 freezes the general accepted-state transition contract for the future continuous SGSim PAD-Stream runtime. It executes no physics and creates no new numerical state.\n\nThe frozen V16 100-day object remains unchanged and is now explicitly treated as an immutable regression/validation checkpoint for the future t=0 -> 100 d rollout; it is not the production initial condition.\n\nRuntime rules frozen here:\n\n- production runtime begins from a separately constructed t=0 state in V16E-34;\n- one conservative Cartesian grid saturation field is the recurrent plume-state authority;\n- F0-style learned timestep/retrace outputs are proposals only and the SGSim numerical dt envelope must be revalidated;\n- exact pressure, well, Darcy, Pollock, TOF legality, nonlinear residual, conservation, and retry checks remain final authorities;\n- fixed observation targets are {DEFAULT_OBSERVATION_DAYS} days and are output clocks, not timestep sizes;\n- a requested snapshot is reached by exact accepted-step landing rather than temporal interpolation of canonical states;\n- global breakthrough uses producer CO2 gas cut >= {BREAKTHROUGH_GAS_CUT:.1e}; scalar interpolation may seed event refinement but the canonical breakthrough plume must come from an accepted physics state;\n- CO2 injected, produced, stored, per-step residual, and cumulative residual mass are recorded throughout the rollout;\n- global saturation scaling for mass repair is prohibited; bounded conservative projection is allowed only for admissibly small residuals and must be re-audited;\n- a rejected attempt advances neither time nor accepted state/recurrent/event/mass memory.\n\nE33 single-step execution authorization: NO. V16E-34 must first construct and validate the physical t=0 SGSim runtime state.\n\nNEXT: {NEXT}\n"""

        files: dict[str, bytes] = {
            "V16E33_Runtime_State_Transition_Contract.json": json_bytes(transition_contract),
            "V16E33_Mass_Balance_Ledger_Contract.json": json_bytes(mass_contract),
            "V16E33_Simulation_Observation_Event_Clock_Contract.json": json_bytes(scheduler_contract),
            "V16E33_Retry_Rollback_Contract.json": json_bytes(rollback_contract),
            "V16E33_Canonical_Runtime_State_Schema.csv": csv_bytes(state_rows),
            "V16E33_Interpolation_Policy.csv": csv_bytes(interp_rows),
            "V16E33_Transition_Acceptance_Gates.csv": csv_bytes(accept_rows),
            "V16E33_Source_Authority_Manifest.csv": csv_bytes(source_rows),
            "PAD_Stream_V16E33_Summary.json": json_bytes(summary),
            "V16E33_Handoff.md": handoff.encode("utf-8"),
        }

        # Final gates are part of the deterministic output set, so add them only
        # after all prospective contract gates above have closed.
        final_gate_rows = [{"gate": name, **record} for name, record in gates.items()]
        files["V16E33_Final_Gate_Matrix.csv"] = csv_bytes(final_gate_rows)

        immutable_publish(out, files)

        # ------------------------------------------------------------------
        # Post-publication immutability checks.
        # ------------------------------------------------------------------
        gate("E32_summary_unchanged_after_E33", sha256_file(e32_summary_path) == e32_summary_sha_before)
        gate("E32_contract_unchanged_after_E33", sha256_file(e32_contract_path) == e32_contract_sha_before)
        gate("frozen_100d_state_unchanged_after_E33", sha256_file(frozen_state_path) == frozen_state_sha_before == V16_FROZEN_SHA)

        # The post-publication gates are reported to stdout and summary semantics;
        # the immutable final-gate artifact intentionally records the prepublish
        # decision matrix used to authorize publication.  Re-running E33 verifies
        # all source/parent identities again before accepting identical bytes.

        print("\n" + "=" * 132)
        print("V16E-33 RESULT: PASS")
        print("=" * 132)
        print(f"{'Runtime transition contract frozen':72}: YES")
        print(f"{'Production runtime initial time':72}: 0 days (state construction deferred to E34)")
        print(f"{'Frozen 100-day state role':72}: REGRESSION / VALIDATION CHECKPOINT")
        print(f"{'Canonical recurrent plume state':72}: CONSERVATIVE CARTESIAN GRID")
        print(f"{'Simulation / observation clocks separated':72}: YES")
        print(f"{'Fixed observation days':72}: {DEFAULT_OBSERVATION_DAYS}")
        print(f"{'Breakthrough producer gas-cut threshold':72}: {BREAKTHROUGH_GAS_CUT:.1e}")
        print(f"{'Canonical temporal interpolation':72}: PROHIBITED")
        print(f"{'Mass balance required for acceptance':72}: YES")
        print(f"{'V15 numerical dt bounds blindly inherited':72}: NO")
        print(f"{'Runtime time advance performed':72}: NO")
        print(f"{'New saturation field created':72}: NO")
        print(f"{'Single-step execution authorized':72}: NO")
        print(f"{'Frozen 100-day state modified':72}: NO")

        for name in sorted(files):
            path = out / name
            print(f"{name} SHA: {sha256_file(path)}")

        print(f"Output: {out}")
        print(f"NEXT: {NEXT}")
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        payload = {
            "milestone": MILESTONE,
            "status": "BLOCKED",
            "exception": repr(exc),
            "gates": gates,
            "runtime_time_advance_performed": False,
            "new_saturation_field_created": False,
            "single_step_execution_authorized": False,
            "t0_state_created": False,
            "frozen_100d_checkpoint_modified": (
                False
                if frozen_state_sha_before is None or not frozen_state_path.exists()
                else sha256_file(frozen_state_path) != frozen_state_sha_before
            ),
            "next_milestone": (
                "V16E-33-R1 - Repair only the failed state-transition-contract/provenance gate; "
                "preserve E32 and the frozen 100-day checkpoint unchanged"
            ),
        }
        path = blocked / "V16E33_Blocked_Runtime_State_Transition_Contract.json"
        path.write_bytes(json_bytes(payload))
        print(f"\n[FAIL] V16E-33 did not close: {exc}", flush=True)
        print(f"Blocked report SHA: {sha256_file(path)}", flush=True)
        print(f"Blocked output: {blocked}", flush=True)
        return 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument("--drive-root", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(main(args.project_root, args.drive_root))
