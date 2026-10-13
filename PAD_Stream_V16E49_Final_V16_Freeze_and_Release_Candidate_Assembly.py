from __future__ import annotations

from pathlib import Path
import argparse
import csv
import hashlib
import io
import json
import math
import subprocess
from typing import Any

import numpy as np


MILESTONE = "V16E-49"
STATUS = "FINAL_V16_FREEZE_AND_RELEASE_CANDIDATE_ASSEMBLED"
NEXT = "V16 Visual Package - SGSim + PAD-Stream Architecture and Runtime Results"

RELEASE_NAME = "PAD-Stream V16"
RELEASE_CANDIDATE = "RC1"
OBSERVATION_DAYS = [30.0, 60.0, 100.0, 150.0, 250.0, 365.0, 500.0, 750.0, 1000.0]
OBSERVATION_STEPS = [611, 1222, 4640, 5747, 7931, 10400, 13259, 18490, 23668]
PRODUCTION_POLICY = "HALF_OBSERVED_STALE_INTERVAL"
MAX_FLOW_EPOCH_DAYS = 4.9417335239115445
TERMINAL_DAY = 1000.0
TERMINAL_STEP = 23668
TERMINAL_RESTART_SHA256 = "af0097b5e7befc7417286fbb90cc2139a3dab583cb3cce972c9293c7b7fe0a7e"
LEGACY_SHA256 = "d422dc1e56281c1baf0ae007c62ce4bd69677a232bd1448a5bd79d3177eafaea"

E48_RUNNER = "PAD_Stream_V16E48_Long_Horizon_Runtime_Closure_and_V16_Integration_Audit.py"
E48_GIT_BLOB = "7bec03cb1e8c3710f8fff6a457513a4e9e510872"
E47_RUNNER = "PAD_Stream_V16E47_Repaired_Production_Continuation_to_Exact_1000Day_Observation.py"
E47_GIT_BLOB = "b3f6a4212e18e13239eb7bd5703c43484b376dcb"
R3R6_RUNNER = "PAD_Stream_V16E41R3R6_Production_Runtime_Refresh_Policy_Freeze.py"
R3R6_GIT_BLOB = "58f17776a1e72baece909a67ff6e1ca7135adf6a"
R3R8_RUNNER = "PAD_Stream_V16E41R3R8_100Day_Legacy_Numerical_Regression_and_E41_Closure.py"
R3R8_GIT_BLOB = "607536622c3b0ff0d4aef451652e724ad4689baa"

E48_REL = Path(
    "provenance/hybrid_dp/"
    "V16E48_LONG_HORIZON_RUNTIME_CLOSURE_AND_V16_INTEGRATION_AUDIT"
)
E48_SUMMARY = "PAD_Stream_V16E48_Summary.json"
E48_CLOSURE = "V16E48_Final_Closure.json"
E48_FREEZE_READINESS = "V16E48_Freeze_Readiness.json"
E48_RUNTIME_POLICY = "V16E48_Runtime_Policy_Audit.json"
E48_SOURCE_BINDINGS = "V16E48_Source_Bindings.csv"
E48_OBSERVATION_AUDIT = "V16E48_Observation_Lineage_and_Mass_Audit.csv"
E48_CAPACITY_AUDIT = "V16E48_Capacity_Safety_Audit.csv"
E48_MANIFEST = "V16E48_Artifact_Manifest.csv"
EXPECTED_E48_STATUS = "LONG_HORIZON_RUNTIME_CLOSURE_AND_V16_INTEGRATION_AUDIT_VALIDATED"

E47_REL = Path(
    "provenance/hybrid_dp/"
    "V16E47_REPAIRED_PRODUCTION_EXACT_1000D_OBSERVATION"
)
E47_RESTART = "V16E47_Authoritative_1000d_PostObservation_Refreshed_Restart.npz"

POLICY_REL = Path(
    "provenance/hybrid_dp/"
    "V16E41R3R6_PRODUCTION_RUNTIME_REFRESH_POLICY_FREEZE"
)
POLICY_CONTRACT = "PAD_Stream_V16E41R3R6_Production_Runtime_Refresh_Policy_Contract.json"
POLICY_CLOSURE = "V16E41R3R6_Final_Closure.json"

E41_REL = Path(
    "provenance/hybrid_dp/"
    "V16E41R3R8_100D_LEGACY_NUMERICAL_REGRESSION_AND_E41_CLOSURE"
)
E41_SUMMARY = "PAD_Stream_V16E41R3R8_Summary.json"
E41_CLOSURE = "V16E41R3R8_Final_Closure.json"
EXPECTED_E41_STATUS = "E41_REPAIRED_100D_PRODUCTION_AND_LEGACY_NUMERICAL_REGRESSION_CLOSED"

LEGACY_REL = Path(
    "provenance/hybrid_dp/"
    "V16E18_R1_FROZEN_SGSIM_100D_FULL_GRID_CANDIDATE/"
    "frozen_full_grid/"
    "V16E18_R1_Frozen_SGSim_100Day_Full_Grid_Candidate.npz"
)

OUT_REL = Path(
    "provenance/hybrid_dp/"
    "V16E49_FINAL_V16_FREEZE_AND_RELEASE_CANDIDATE"
)
BLOCKED_REL = Path(
    "provenance/hybrid_dp/"
    "V16E49_BLOCKED_FINAL_V16_FREEZE_AND_RELEASE_CANDIDATE"
)

EXPECTED_E48_SOURCE_ROLES = {
    "E39", "E40", "R3R6", "R3R7", "R3R8",
    "E42", "E43", "E44R1", "E45", "E46", "E47",
}

V16_ARCHITECTURE_CONTRACT = {
    "geology": "SGSim 50x50x15 dissertation-base heterogeneous permeability model",
    "pressure": "saturation-updated finite-volume pressure solve with same-time mass-conservative refresh reconciliation",
    "darcy_flux": "conservative finite-volume Darcy face fluxes",
    "streamlines": "exact 3D Pollock tracing",
    "transport_coordinate": "time-of-flight / normalized streamline coordinate",
    "transport_primary_variable": "CO2 component mass in streamline finite volumes",
    "streamline_grid_transfer": "E37A control-volume-aligned conservative transfer using SG7D exact overlap geometry",
    "capillary": "no-flow conservative Cartesian capillary mass redistribution with zero external mass source",
    "runtime_refresh_policy": PRODUCTION_POLICY,
    "maximum_flow_epoch_age_days": MAX_FLOW_EPOCH_DAYS,
    "capacity_controller_role": "last-resort fallback only after same-parent full flow refresh",
    "observation_schedule_days": OBSERVATION_DAYS,
    "terminal_observation_day": TERMINAL_DAY,
}

V16_VISUAL_PACKAGE_REQUIREMENTS = [
    "SGSim reservoir geometry and permeability heterogeneity",
    "pressure field",
    "Darcy face fluxes",
    "Pollock streamlines",
    "time-of-flight field",
    "CO2 plume evolution at V16 observation checkpoints",
    "PAD-Stream full architecture and runtime flow",
]


class GateError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def json_bytes(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        return b""
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue().encode("utf-8")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_npz(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as z:
        return {k: z[k].copy() for k in z.files}


def scalar(value: Any) -> float:
    return float(np.asarray(value).reshape(()))


def int_scalar(value: Any) -> int:
    return int(np.asarray(value).reshape(()))


def bool_scalar(value: Any) -> bool:
    return bool(np.asarray(value).reshape(()))


def git_blob_sha(path: Path, root: Path) -> str:
    proc = subprocess.run(
        ["git", "-C", str(root), "hash-object", str(path)],
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


def self_test() -> None:
    if RELEASE_NAME != "PAD-Stream V16":
        raise RuntimeError("release_name_identity")
    if RELEASE_CANDIDATE != "RC1":
        raise RuntimeError("release_candidate_identity")
    if OBSERVATION_DAYS != [30.0, 60.0, 100.0, 150.0, 250.0, 365.0, 500.0, 750.0, 1000.0]:
        raise RuntimeError("observation_schedule_identity")
    if OBSERVATION_STEPS != [611, 1222, 4640, 5747, 7931, 10400, 13259, 18490, 23668]:
        raise RuntimeError("observation_step_identity")
    if TERMINAL_DAY != 1000.0 or TERMINAL_STEP != 23668:
        raise RuntimeError("terminal_identity")
    if PRODUCTION_POLICY != "HALF_OBSERVED_STALE_INTERVAL":
        raise RuntimeError("policy_identity")
    if abs(MAX_FLOW_EPOCH_DAYS - 4.9417335239115445) > 1.0e-15:
        raise RuntimeError("epoch_identity")
    if len(V16_VISUAL_PACKAGE_REQUIREMENTS) != 7:
        raise RuntimeError("visual_requirement_count")
    print("PAD-Stream V16E-49 final V16 freeze / release-candidate self-test: PASS")


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
        print("\n" + "=" * 164)
        print("PAD-Stream V16E-49 — Final V16 Freeze and Release-Candidate Assembly")
        print("=" * 164)
        print("SIMULATION : none")
        print("MUTATION   : freeze metadata only; no accepted runtime state is altered")
        print("RELEASE    :", RELEASE_NAME, RELEASE_CANDIDATE)
        print("TERMINAL   :", TERMINAL_STEP, "/", TERMINAL_DAY, "d")
        print("PURPOSE    : convert E48 authorization into an immutable V16 release contract")

        failed_stage = "source_identity"
        current_sources = [
            ("E48", E48_RUNNER, E48_GIT_BLOB),
            ("E47", E47_RUNNER, E47_GIT_BLOB),
            ("R3R6", R3R6_RUNNER, R3R6_GIT_BLOB),
            ("R3R8", R3R8_RUNNER, R3R8_GIT_BLOB),
        ]
        source_rows: list[dict[str, Any]] = []
        for role, filename, expected_blob in current_sources:
            p = root / filename
            gate(f"{role}_runner_exists", p.is_file(), p)
            actual = git_blob_sha(p, root)
            gate(f"{role}_git_blob_exact", actual == expected_blob, actual)
            source_rows.append({
                "role": role,
                "filename": filename,
                "expected_git_blob": expected_blob,
                "actual_git_blob": actual,
            })

        failed_stage = "E48_authorization_integrity"
        e48_base = drive / E48_REL
        required_e48 = [
            E48_SUMMARY,
            E48_CLOSURE,
            E48_FREEZE_READINESS,
            E48_RUNTIME_POLICY,
            E48_SOURCE_BINDINGS,
            E48_OBSERVATION_AUDIT,
            E48_CAPACITY_AUDIT,
            E48_MANIFEST,
        ]
        for name in required_e48:
            gate(f"E48_artifact_exists_{name}", (e48_base / name).is_file(), e48_base / name)

        # Validate E48's own artifact manifest before trusting its authorization.
        e48_manifest = load_csv(e48_base / E48_MANIFEST)
        gate("E48_manifest_nonempty", len(e48_manifest) >= 8, len(e48_manifest))
        for row in e48_manifest:
            p = e48_base / row["file"]
            gate(f"E48_manifest_file_exists_{row['file']}", p.is_file(), p)
            actual_sha = sha256_file(p)
            gate(
                f"E48_manifest_SHA_exact_{row['file']}",
                actual_sha == row["sha256"],
                actual_sha,
            )
            gate(
                f"E48_manifest_size_exact_{row['file']}",
                p.stat().st_size == int(row["bytes"]),
                p.stat().st_size,
            )

        e48_summary = load_json(e48_base / E48_SUMMARY)
        e48_closure = load_json(e48_base / E48_CLOSURE)
        e48_freeze = load_json(e48_base / E48_FREEZE_READINESS)
        e48_policy = load_json(e48_base / E48_RUNTIME_POLICY)

        gate("E48_status_exact", e48_summary.get("status") == EXPECTED_E48_STATUS, e48_summary.get("status"))
        gate("E48_all_gates_passed", e48_closure.get("all_gates_passed") is True, e48_closure.get("all_gates_passed"))
        gate("E48_runtime_closed", e48_closure.get("long_horizon_runtime_closed") is True, e48_closure.get("long_horizon_runtime_closed"))
        gate("E48_schedule_complete", e48_closure.get("observation_schedule_complete") is True, e48_closure.get("observation_schedule_complete"))
        gate("E48_final_freeze_authorized", e48_closure.get("V16_final_freeze_authorized") is True, e48_closure.get("V16_final_freeze_authorized"))
        gate("E48_freeze_readiness_authorized", e48_freeze.get("V16_final_freeze_authorized") is True, e48_freeze.get("V16_final_freeze_authorized"))
        gate("E48_no_new_physics_required", e48_freeze.get("new_physics_required_before_final_V16_freeze") is False, e48_freeze.get("new_physics_required_before_final_V16_freeze"))
        gate("E48_no_new_calibration_required", e48_freeze.get("new_calibration_required_before_final_V16_freeze") is False, e48_freeze.get("new_calibration_required_before_final_V16_freeze"))
        gate("E48_capacity_fallback_unused", e48_closure.get("capacity_fallback_used_100_to_1000d") is False, e48_closure.get("capacity_fallback_used_100_to_1000d"))
        gate("E48_terminal_restart_SHA_exact", e48_closure.get("terminal_restart_sha256") == TERMINAL_RESTART_SHA256, e48_closure.get("terminal_restart_sha256"))
        gate("E48_terminal_step_exact", int(e48_closure.get("terminal_observation_step")) == TERMINAL_STEP, e48_closure.get("terminal_observation_step"))
        gate("E48_terminal_day_exact", float(e48_closure.get("terminal_observation_day")) == TERMINAL_DAY, e48_closure.get("terminal_observation_day"))
        gate("E48_policy_name_exact", e48_policy.get("policy_name") == PRODUCTION_POLICY, e48_policy.get("policy_name"))
        gate("E48_policy_epoch_exact", abs(float(e48_policy.get("maximum_flow_epoch_age_days")) - MAX_FLOW_EPOCH_DAYS) <= 1.0e-15, e48_policy.get("maximum_flow_epoch_age_days"))

        inherited_sources = load_csv(e48_base / E48_SOURCE_BINDINGS)
        inherited_roles = {row["role"] for row in inherited_sources}
        gate("E48_source_role_set_exact", inherited_roles == EXPECTED_E48_SOURCE_ROLES, inherited_roles)
        gate(
            "E48_inherited_source_bindings_all_exact",
            all(row["expected_git_blob"] == row["actual_git_blob"] for row in inherited_sources),
        )

        observation_rows = load_csv(e48_base / E48_OBSERVATION_AUDIT)
        gate("E48_observation_count_exact", len(observation_rows) == 9, len(observation_rows))
        gate(
            "E48_observation_days_exact",
            [float(r["day"]) for r in observation_rows] == OBSERVATION_DAYS,
            [r["day"] for r in observation_rows],
        )
        gate(
            "E48_observation_steps_exact",
            [int(r["step"]) for r in observation_rows] == OBSERVATION_STEPS,
            [r["step"] for r in observation_rows],
        )

        capacity_rows = load_csv(e48_base / E48_CAPACITY_AUDIT)
        gate("E48_capacity_audit_nonempty", len(capacity_rows) >= 7, len(capacity_rows))
        capacity_margins = [float(r["minimum_raw_capacity_margin_kg"]) for r in capacity_rows]
        capacity_refreshes = sum(int(r["capacity_refresh_count"]) for r in capacity_rows)
        capacity_adjustments = sum(int(r["capacity_controller_adjustments_total"]) for r in capacity_rows)
        gate("E48_all_capacity_margins_positive", min(capacity_margins) > 0.0, min(capacity_margins))
        gate("E48_capacity_refreshes_zero", capacity_refreshes == 0, capacity_refreshes)
        gate("E48_capacity_adjustments_zero", capacity_adjustments == 0, capacity_adjustments)

        failed_stage = "terminal_restart_integrity"
        terminal_path = drive / E47_REL / E47_RESTART
        gate("terminal_restart_exists", terminal_path.is_file(), terminal_path)
        terminal_sha = sha256_file(terminal_path)
        gate("terminal_restart_SHA_exact", terminal_sha == TERMINAL_RESTART_SHA256, terminal_sha)

        terminal = load_npz(terminal_path)
        gate("terminal_time_exact", scalar(terminal["physical_time_days"]) == TERMINAL_DAY, scalar(terminal["physical_time_days"]))
        gate("terminal_step_exact", int_scalar(terminal["accepted_step_index"]) == TERMINAL_STEP, int_scalar(terminal["accepted_step_index"]))
        gate("terminal_cursor_exact", int_scalar(terminal["observation_cursor_index"]) == 9, int_scalar(terminal["observation_cursor_index"]))
        gate("terminal_last_observation_exact", scalar(terminal["last_fixed_observation_day"]) == TERMINAL_DAY, scalar(terminal["last_fixed_observation_day"]))
        gate("terminal_next_observation_nan", math.isnan(scalar(terminal["next_fixed_observation_day"])), scalar(terminal["next_fixed_observation_day"]))
        gate(
            "terminal_schedule_complete_flag",
            "fixed_observation_schedule_complete" in terminal
            and bool_scalar(terminal["fixed_observation_schedule_complete"]),
        )
        gate(
            "terminal_authoritative_restart_flag",
            "V16E47_authoritative_post_observation_restart" in terminal
            and bool_scalar(terminal["V16E47_authoritative_post_observation_restart"]),
        )
        gate(
            "terminal_injected_mass_500Mkg",
            abs(scalar(terminal["cumulative_injected_co2_mass_kg"]) - 500_000_000.0) <= 5.0e-4,
            scalar(terminal["cumulative_injected_co2_mass_kg"]),
        )

        failed_stage = "frozen_policy_E41_legacy_integrity"
        policy_contract_path = drive / POLICY_REL / POLICY_CONTRACT
        policy_closure_path = drive / POLICY_REL / POLICY_CLOSURE
        gate("policy_contract_exists", policy_contract_path.is_file(), policy_contract_path)
        gate("policy_closure_exists", policy_closure_path.is_file(), policy_closure_path)
        policy_contract = load_json(policy_contract_path)
        policy_closure = load_json(policy_closure_path)
        gate("policy_frozen_status_exact", policy_contract.get("status") == "PRODUCTION_RUNTIME_REFRESH_POLICY_FROZEN", policy_contract.get("status"))
        gate("policy_closure_passed", policy_closure.get("all_gates_passed") is True, policy_closure.get("all_gates_passed"))
        gate("policy_name_exact", policy_contract["calibrated_policy"]["name"] == PRODUCTION_POLICY, policy_contract["calibrated_policy"]["name"])
        gate("policy_epoch_exact", abs(float(policy_contract["calibrated_policy"]["maximum_flow_epoch_age_days"]) - MAX_FLOW_EPOCH_DAYS) <= 1.0e-15)
        gate("policy_visual_requirements_exact", policy_contract.get("V16_closeout_visuals_required") == V16_VISUAL_PACKAGE_REQUIREMENTS, policy_contract.get("V16_closeout_visuals_required"))

        e41_summary_path = drive / E41_REL / E41_SUMMARY
        e41_closure_path = drive / E41_REL / E41_CLOSURE
        gate("E41_summary_exists", e41_summary_path.is_file(), e41_summary_path)
        gate("E41_closure_exists", e41_closure_path.is_file(), e41_closure_path)
        e41_summary = load_json(e41_summary_path)
        e41_closure = load_json(e41_closure_path)
        gate("E41_status_exact", e41_summary.get("status") == EXPECTED_E41_STATUS, e41_summary.get("status"))
        gate("E41_formally_closed", e41_summary.get("E41_closed") is True and e41_closure.get("E41_closed") is True)

        legacy_path = drive / LEGACY_REL
        gate("legacy_candidate_exists", legacy_path.is_file(), legacy_path)
        legacy_sha = sha256_file(legacy_path)
        gate("legacy_candidate_SHA_exact", legacy_sha == LEGACY_SHA256, legacy_sha)

        failed_stage = "release_candidate_assembly"

        # Capture a compact immutable basis for the release identity.
        inherited_source_snapshot = [
            {
                "role": row["role"],
                "filename": row["filename"],
                "git_blob": row["actual_git_blob"],
            }
            for row in inherited_sources
        ]
        inherited_source_snapshot.append({
            "role": "E48",
            "filename": E48_RUNNER,
            "git_blob": E48_GIT_BLOB,
        })

        release_basis = {
            "release_name": RELEASE_NAME,
            "release_candidate": RELEASE_CANDIDATE,
            "terminal_restart_sha256": TERMINAL_RESTART_SHA256,
            "legacy_candidate_sha256": LEGACY_SHA256,
            "E48_runner_git_blob": E48_GIT_BLOB,
            "E48_closure_sha256": sha256_file(e48_base / E48_CLOSURE),
            "E48_freeze_readiness_sha256": sha256_file(e48_base / E48_FREEZE_READINESS),
            "R3R6_policy_contract_sha256": sha256_file(policy_contract_path),
            "E41_closure_sha256": sha256_file(e41_closure_path),
            "observation_days": OBSERVATION_DAYS,
            "observation_steps": OBSERVATION_STEPS,
            "production_policy": PRODUCTION_POLICY,
            "maximum_flow_epoch_age_days": MAX_FLOW_EPOCH_DAYS,
            "architecture_contract": V16_ARCHITECTURE_CONTRACT,
            "accepted_source_bindings": inherited_source_snapshot,
        }
        release_basis_bytes = json_bytes(release_basis)
        release_basis_sha = hashlib.sha256(release_basis_bytes).hexdigest()
        release_id = f"PAD-STREAM-V16-RC1-{release_basis_sha[:16].upper()}"

        # Final authoritative release manifest. Large runtime artifacts are frozen by path+SHA,
        # not copied or rewritten.
        e48_manifest_map = {r["file"]: r["sha256"] for r in e48_manifest}
        release_manifest = [
            {
                "role": "terminal_authoritative_runtime_state",
                "path": str(E47_REL / E47_RESTART),
                "sha256": TERMINAL_RESTART_SHA256,
                "mutable_after_freeze": False,
            },
            {
                "role": "long_horizon_closure",
                "path": str(E48_REL / E48_CLOSURE),
                "sha256": e48_manifest_map[E48_CLOSURE],
                "mutable_after_freeze": False,
            },
            {
                "role": "freeze_readiness",
                "path": str(E48_REL / E48_FREEZE_READINESS),
                "sha256": e48_manifest_map[E48_FREEZE_READINESS],
                "mutable_after_freeze": False,
            },
            {
                "role": "observation_lineage_mass_audit",
                "path": str(E48_REL / E48_OBSERVATION_AUDIT),
                "sha256": e48_manifest_map[E48_OBSERVATION_AUDIT],
                "mutable_after_freeze": False,
            },
            {
                "role": "capacity_safety_audit",
                "path": str(E48_REL / E48_CAPACITY_AUDIT),
                "sha256": e48_manifest_map[E48_CAPACITY_AUDIT],
                "mutable_after_freeze": False,
            },
            {
                "role": "production_runtime_policy_contract",
                "path": str(POLICY_REL / POLICY_CONTRACT),
                "sha256": sha256_file(policy_contract_path),
                "mutable_after_freeze": False,
            },
            {
                "role": "E41_repaired_regression_closure",
                "path": str(E41_REL / E41_CLOSURE),
                "sha256": sha256_file(e41_closure_path),
                "mutable_after_freeze": False,
            },
            {
                "role": "legacy_numerical_regression_candidate",
                "path": str(LEGACY_REL),
                "sha256": LEGACY_SHA256,
                "mutable_after_freeze": False,
            },
        ]

        freeze_contract = {
            "milestone": MILESTONE,
            "status": STATUS,
            "release_id": release_id,
            "release_basis_sha256": release_basis_sha,
            "release_name": RELEASE_NAME,
            "release_candidate": RELEASE_CANDIDATE,
            "V16_frozen": True,
            "simulation_executed": False,
            "accepted_runtime_architecture": V16_ARCHITECTURE_CONTRACT,
            "authoritative_terminal_state": {
                "day": TERMINAL_DAY,
                "step": TERMINAL_STEP,
                "restart_filename": E47_RESTART,
                "restart_path": str(E47_REL / E47_RESTART),
                "restart_sha256": TERMINAL_RESTART_SHA256,
                "observation_schedule_complete": True,
                "next_fixed_observation": None,
            },
            "accepted_observation_schedule": {
                "days": OBSERVATION_DAYS,
                "steps": OBSERVATION_STEPS,
            },
            "runtime_safety_closure": {
                "minimum_raw_capacity_margin_kg": min(capacity_margins),
                "capacity_triggered_refresh_count": capacity_refreshes,
                "capacity_controller_adjustments": capacity_adjustments,
                "component_mass_conservation_required": True,
                "mass_clipping_authorized": False,
                "global_plume_rescaling_authorized": False,
            },
            "legacy_regression_semantics": {
                "legacy_candidate_sha256": LEGACY_SHA256,
                "candidate_is_physical_truth": False,
                "candidate_role": "historical numerical regression candidate only",
                "E41_regression_formally_closed": True,
            },
            "immutability_policy": {
                "frozen_runtime_physics_modification_authorized": False,
                "frozen_observation_states_modification_authorized": False,
                "frozen_source_lineage_rewrite_authorized": False,
                "post_freeze_new_research_must_be_versioned_after_V16": True,
                "exception": (
                    "A demonstrated provenance or implementation defect affecting freeze integrity "
                    "requires a separately versioned repair and re-freeze; it must not silently mutate V16."
                ),
            },
            "post_freeze_scope": {
                "next_required_work": NEXT,
                "visual_package_requirements": V16_VISUAL_PACKAGE_REQUIREMENTS,
                "IBDP_work_begins_before_visual_closeout": False,
                "new_V16_calibration_authorized": False,
                "new_V16_physics_branch_authorized": False,
            },
        }

        release_certificate = {
            "release_id": release_id,
            "release_name": RELEASE_NAME,
            "release_candidate": RELEASE_CANDIDATE,
            "V16_frozen": True,
            "runtime_closed_through_day": TERMINAL_DAY,
            "terminal_step": TERMINAL_STEP,
            "terminal_restart_sha256": TERMINAL_RESTART_SHA256,
            "observation_schedule_complete": True,
            "production_policy": PRODUCTION_POLICY,
            "maximum_flow_epoch_age_days": MAX_FLOW_EPOCH_DAYS,
            "E41_formally_closed": True,
            "E48_final_freeze_authorized": True,
            "capacity_fallback_used_100_to_1000d": False,
            "legacy_candidate_is_truth": False,
            "next": NEXT,
        }

        summary = {
            "milestone": MILESTONE,
            "status": STATUS,
            "release_id": release_id,
            "release_basis_sha256": release_basis_sha,
            "V16_frozen": True,
            "simulation_executed": False,
            "terminal_day": TERMINAL_DAY,
            "terminal_step": TERMINAL_STEP,
            "terminal_restart_sha256": TERMINAL_RESTART_SHA256,
            "observation_schedule_complete": True,
            "observation_days": OBSERVATION_DAYS,
            "minimum_raw_capacity_margin_kg": min(capacity_margins),
            "capacity_triggered_refreshes_100_to_1000d": capacity_refreshes,
            "capacity_controller_adjustments_100_to_1000d": capacity_adjustments,
            "E41_closed": True,
            "E48_freeze_authorization_consumed": True,
            "legacy_candidate_sha256": LEGACY_SHA256,
            "visual_package_required": True,
            "next_milestone": NEXT,
        }

        gate("release_manifest_has_terminal_state", release_manifest[0]["sha256"] == TERMINAL_RESTART_SHA256)
        gate("freeze_contract_marks_V16_frozen", freeze_contract["V16_frozen"] is True)
        gate("freeze_contract_forbids_silent_runtime_mutation", freeze_contract["immutability_policy"]["frozen_runtime_physics_modification_authorized"] is False)
        gate("freeze_contract_requires_visual_package", freeze_contract["post_freeze_scope"]["visual_package_requirements"] == V16_VISUAL_PACKAGE_REQUIREMENTS)
        gate("release_certificate_marks_V16_frozen", release_certificate["V16_frozen"] is True)

        closure = {
            "milestone": MILESTONE,
            "status": STATUS,
            "all_gates_passed": all(v["passed"] for v in gates.values()),
            "gate_count": len(gates),
            "release_id": release_id,
            "release_basis_sha256": release_basis_sha,
            "V16_frozen": True,
            "V16_release_candidate_assembled": True,
            "terminal_runtime_state_frozen": True,
            "production_runtime_policy_frozen": True,
            "observation_schedule_frozen": True,
            "source_lineage_frozen": True,
            "E41_formally_closed": True,
            "E48_authorization_consumed": True,
            "new_V16_simulation_development_authorized": False,
            "next": NEXT,
        }

        files = {
            "PAD_Stream_V16E49_Summary.json": json_bytes(summary),
            "PAD_Stream_V16_Final_Freeze_Contract.json": json_bytes(freeze_contract),
            "PAD_Stream_V16_Release_Certificate.json": json_bytes(release_certificate),
            "PAD_Stream_V16_Release_Basis.json": release_basis_bytes,
            "PAD_Stream_V16_Release_Candidate_Manifest.csv": csv_bytes(release_manifest),
            "V16E49_Source_Bindings.csv": csv_bytes(source_rows),
            "V16E49_Inherited_E48_Source_Bindings.csv": csv_bytes(inherited_sources),
            "V16E49_Final_Gate_Matrix.csv": csv_bytes([{"gate": k, **v} for k, v in gates.items()]),
            "V16E49_Final_Closure.json": json_bytes(closure),
        }
        immutable_publish(out, files)

        manifest: list[dict[str, Any]] = []
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name != "V16E49_Artifact_Manifest.csv":
                manifest.append({
                    "file": p.name,
                    "sha256": sha256_file(p),
                    "bytes": p.stat().st_size,
                })
        immutable_publish(out, {"V16E49_Artifact_Manifest.csv": csv_bytes(manifest)})

        print("\n" + "=" * 164)
        print("PAD-Stream V16E-49: PASS")
        print("=" * 164)
        print(f"{'Status':72}: {STATUS}")
        print(f"{'Release ID':72}: {release_id}")
        print(f"{'V16 frozen':72}: True")
        print(f"{'Terminal step / time':72}: {TERMINAL_STEP} / {TERMINAL_DAY} d")
        print(f"{'Terminal restart SHA':72}: {TERMINAL_RESTART_SHA256}")
        print(f"{'Observation schedule complete':72}: True")
        print(f"{'Minimum raw capacity margin':72}: {min(capacity_margins):.12f} kg")
        print(f"{'Capacity-triggered refreshes 100->1000d':72}: {capacity_refreshes}")
        print(f"{'Capacity-controller adjustments 100->1000d':72}: {capacity_adjustments}")
        print(f"{'E41 formally closed':72}: True")
        print(f"{'E48 authorization consumed':72}: True")
        print(f"{'New V16 simulation development authorized':72}: False")
        print(f"{'Next':72}: {NEXT}")
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": MILESTONE,
            "status": "FINAL_V16_FREEZE_AND_RELEASE_CANDIDATE_BLOCKED",
            "failed_stage": failed_stage,
            "exception": repr(exc),
            "gates": gates,
        }
        data = json_bytes(report)
        p = blocked / "V16E49_Blocked_Final_V16_Freeze.json"
        if p.exists() and p.read_bytes() != data:
            p = blocked / (
                "V16E49_Blocked_Final_V16_Freeze_"
                + hashlib.sha256(data).hexdigest()[:12]
                + ".json"
            )
        p.write_bytes(data)
        print("\n" + "=" * 164)
        print("PAD-Stream V16E-49: BLOCKED")
        print("=" * 164)
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
