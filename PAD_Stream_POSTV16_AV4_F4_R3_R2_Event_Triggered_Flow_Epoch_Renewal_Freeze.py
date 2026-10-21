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


MILESTONE = "POSTV16-AV4-F4-R3-R2"

STATUS_PASS = (
    "AV4F4R3R2_R3R1R2_INTERIOR_UPPER_CAPACITY_ADVECTION_DOMINATED_CONFLICT_BOUND_"
    "EVENT_TRIGGERED_SAME_TIME_FLOW_EPOCH_RENEWAL_PROSPECTIVELY_FROZEN_"
    "NO_INTERIOR_FACE_LIMITER_NO_REPAIR_EXECUTION"
)
STATUS_BLOCKED = "AV4F4R3R2_EVENT_TRIGGERED_FLOW_EPOCH_RENEWAL_DESIGN_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT_R3R1R2_COMMIT = "2a9d44669c8a87904d85fdf363be7708c1b06e00"

PARENT_DAY = 365.0
EVENT_DAY = 413.78677770818403
TARGET_DAY = 500.0
REMAINING_DAY = 86.21322229181597

OBSERVED = {
    "accepted_substeps_before_failure": 3604,
    "failure_elapsed_days": 48.78677770818403,
    "failure_remaining_days": 86.21322229181597,
    "bound": "UPPER_CAPACITY",
    "streamline": 793,
    "control_volume": 197,
    "mass_fraction": 0.9999999999998449,
    "saturation": 0.7999999999999122,
    "distance_to_bound_kg": 2.930278242274653e-11,
    "rhs_total_kg_day": 0.2370073711253709,
    "rhs_advective_kg_day": 0.23711019070327666,
    "rhs_capillary_kg_day": -0.00010281957790574341,
    "actual_mass_dt_days": 6.181829342186598e-11,
    "advective_only_mass_dt_days": 6.179148676788946e-11,
    "capillary_only_mass_dt_days": 1.5218954835885896,
    "terminal_pass_through_events_before_failure": 8602,
    "terminal_pass_through_unique_streamlines_before_failure": 12,
    "classification": "ADVECTION_DOMINATED_INTERIOR_BOUND_CONFLICT",
}

R3R1R2 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R1_R2_"
    "Corrected_Interior_Bound_Failure_Localization.py"
)
R3R1R2_BLOB = "b7613d8eda48b6e3528115c40faebe46d7b61604"

F4R3 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_"
    "Terminal_Producer_PassThrough_Repair_Execution.py"
)
F4R3_BLOB = "2e84ab09f9ae7af6f977eabc3d9465d325fad717"

F4R2 = "PAD_Stream_POSTV16_AV4_F4_R2_Terminal_Producer_PassThrough_Repair_Freeze.py"
F4R2_BLOB = "d2ce7625d74a27ead60e6669fd11d2c5ffa2dae6"

F4 = "PAD_Stream_POSTV16_AV4_F4_Day365_to_Day500_Restart_Teacher_Certification.py"
F4_BLOB = "a893ab32a1b3a396c3b2242f603c47bc94187a54"

A2E = "PAD_Stream_POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution.py"
A2E_BLOB = "79a8969233b72b4543edd382a0c3d1028c6dca09"

E37A = "PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB = "0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"

R2 = (
    "PAD_Stream_V16E35_R2_Source_Conservative_Transport_"
    "Capillary_Split_First_Controlled_Transition.py"
)
R2_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"

SG2 = "PAD_Stream_V15SG2_Anisotropic_Transmissibility.py"
SG2_BLOB = "7242012d3e758472abc3ee7f543831b92d2cf419"
SG3 = "PAD_Stream_V15SG3_FiveSpot_Pressure_Solve.py"
SG3_BLOB = "66a379cd97ee9120f69e7e7e949171541e4918c3"
SG4 = "PAD_Stream_V15SG4_Conservative_Darcy_Fluxes.py"
SG4_BLOB = "8d49f88bdf55b0da087af2bed04e69967740e695"
SG5 = "PAD_Stream_V15SG5_Exact_Pollock_Streamlines.py"
SG5_BLOB = "9a0b64ea7e669904d0d9855ade1c6b052f05ecea"
SG6 = "PAD_Stream_V15SG6_TOF_Transport_Coordinates.py"
SG6_BLOB = "70ceda68e02894167958d753d88b4dbd694731ab"
SG7D = "PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"
SG7D_BLOB = "890088c0c0fcab415a2c7351c5079ca8ee12bf82"
R3R2R1 = "PAD_Stream_V16E41R3R2R1_Local_Conservation_Sign_Convention_Repair.py"
R3R2R1_BLOB = "740c6da03e73906646bf0153633187e749449f31"

SOURCE_BLOBS = {
    R3R1R2: R3R1R2_BLOB,
    F4R3: F4R3_BLOB,
    F4R2: F4R2_BLOB,
    F4: F4_BLOB,
    A2E: A2E_BLOB,
    E37A: E37A_BLOB,
    R2: R2_BLOB,
    SG2: SG2_BLOB,
    SG3: SG3_BLOB,
    SG4: SG4_BLOB,
    SG5: SG5_BLOB,
    SG6: SG6_BLOB,
    SG7D: SG7D_BLOB,
    R3R2R1: R3R2R1_BLOB,
}

BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

R3R1R2_REL = (
    BASE_AV4
    / "POSTV16_AV4_F4_R3_R1_R2_Corrected_Interior_Bound_Failure_Localization"
)
R3R1R2_SUMMARY = "PAD_Stream_POSTV16_AV4_F4_R3_R1_R2_Summary.json"
R3R1R2_DIAG = "POSTV16_AV4_F4_R3_R1_R2_Interior_Limiter_and_Flux_Diagnosis.json"
R3R1R2_STATE = "POSTV16_AV4_F4_R3_R1_R2_Partial_Teacher_State_at_Failure.npz"
R3R1R2_HANDOFF = "POSTV16_AV4_F4_R3_R1_R2_R3R2_Design_Handoff_Contract.json"
R3R1R2_DECISION = "POSTV16_AV4_F4_R3_R1_R2_Decision_Contract.json"
R3R1R2_MANIFEST = "POSTV16_AV4_F4_R3_R1_R2_Artifact_Manifest.csv"
R3R1R2_STATUS = (
    "AV4F4R3R1R2_R3R1R1_BLOCK_REPORT_FILENAME_AUTHORITY_TYPO_CLOSED_"
    "R3_INTERIOR_MASS_BOUND_SCIENTIFIC_FAIL_PRESERVED_EXACT_INTERIOR_"
    "CV_BOUND_AND_FLUX_MECHANISM_LOCALIZED_NO_REPAIR_SELECTED"
)

OUT_REL = BASE_AV4 / "POSTV16_AV4_F4_R3_R2_Event_Triggered_Flow_Epoch_Renewal_Freeze"
BLOCK_REL = BASE_AV4 / "POSTV16_AV4_F4_R3_R2_BLOCKED"


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
    return (
        json.dumps(obj, indent=2, sort_keys=True, allow_nan=False)
        + "\n"
    ).encode("utf-8")


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
    return s.getvalue().encode("utf-8")


def immutable_publish(out: Path, files: dict[str, bytes]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        p = out / name
        if p.exists() and p.read_bytes() != data:
            raise GateError("existing_output_differs:" + name)
        if not p.exists():
            p.write_bytes(data)


def self_test() -> None:
    assert abs(EVENT_DAY - 413.78677770818403) < 1.0e-12
    assert abs(EVENT_DAY + REMAINING_DAY - TARGET_DAY) < 1.0e-12
    assert OBSERVED["control_volume"] == 197
    assert OBSERVED["bound"] == "UPPER_CAPACITY"
    assert OBSERVED["classification"] == "ADVECTION_DOMINATED_INTERIOR_BOUND_CONFLICT"
    assert (
        abs(OBSERVED["rhs_advective_kg_day"])
        > 1000.0 * abs(OBSERVED["rhs_capillary_kg_day"])
    )
    print(
        "POSTV16-AV4-F4-R3-R2 event-triggered flow-epoch "
        "renewal design self-test: PASS"
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
        "POSTV16-AV4-F4-R3-R2 — EVENT-TRIGGERED SAME-TIME FLOW-EPOCH "
        "RENEWAL DESIGN FREEZE"
    )
    print("=" * 214)
    print("DESIGN / FREEZE ONLY.")
    print("FORMAL F4 AND F4-R3 SCIENTIFIC FAILS REMAIN IMMUTABLE.")
    print("R3-R1-R2 INTERIOR LOCALIZATION REMAINS IMMUTABLE.")
    print("NO INTERIOR FACE LIMITER. NO FLUX REDISTRIBUTION. NO TIMESTEP-FLOOR CHANGE.")
    print("NO REPAIR EXECUTION. NO PHYSICAL-TIME ADVANCE. NO MAPBACK EXECUTION.")
    print("NO FLOW REFRESH EXECUTION. NO REPROJECTION EXECUTION. NO TRAINING. NO CMG.")
    print()

    try:
        stage = "repository_authority"

        parent = git_text(root, "rev-parse", "HEAD^")
        status = git_text(root, "status", "--porcelain")
        gate(
            "repository_parent_is_R3R1R2_commit",
            parent == PARENT_R3R1R2_COMMIT,
            parent,
        )
        gate("repository_clean", status == "", repr(status))

        for fn, expected in SOURCE_BLOBS.items():
            p = root / fn
            actual = git_blob(p, root) if p.is_file() else "missing"
            gate(
                f"{Path(fn).stem}_git_blob_exact",
                actual == expected,
                actual,
            )

        stage = "R3R1R2_localization_binding"

        rd = drive / R3R1R2_REL
        gate("R3R1R2_output_present", rd.is_dir(), str(rd))
        manifest = verify_manifest(rd, R3R1R2_MANIFEST)
        gate("R3R1R2_manifest_exact_8", len(manifest) == 8, len(manifest))
        gate("R3R1R2_partial_state_manifested", R3R1R2_STATE in manifest)

        summary = load_json(rd / R3R1R2_SUMMARY)
        diagnosis = load_json(rd / R3R1R2_DIAG)
        handoff_in = load_json(rd / R3R1R2_HANDOFF)
        decision_in = load_json(rd / R3R1R2_DECISION)

        gate(
            "R3R1R2_status_exact",
            summary["status"] == R3R1R2_STATUS,
            summary["status"],
        )
        gate(
            "historical_scientific_fails_preserved",
            summary["historical_F4_scientific_FAIL_preserved"] is True
            and summary["F4R3_scientific_FAIL_preserved"] is True,
        )
        gate(
            "R3R1R2_mechanism_exact",
            summary["classification"] == OBSERVED["classification"]
            and summary["limiter_bound"] == OBSERVED["bound"]
            and int(summary["limiter_streamline"]) == OBSERVED["streamline"]
            and int(summary["limiter_control_volume"]) == OBSERVED["control_volume"],
            {
                "classification": summary["classification"],
                "bound": summary["limiter_bound"],
                "location": [
                    summary["limiter_streamline"],
                    summary["limiter_control_volume"],
                ],
            },
        )

        numeric = {
            "failure_elapsed_days": OBSERVED["failure_elapsed_days"],
            "failure_remaining_days": OBSERVED["failure_remaining_days"],
            "limiter_mass_fraction": OBSERVED["mass_fraction"],
            "limiter_saturation": OBSERVED["saturation"],
            "limiter_distance_to_bound_kg": OBSERVED["distance_to_bound_kg"],
            "total_rhs_kg_day": OBSERVED["rhs_total_kg_day"],
            "advective_rhs_kg_day": OBSERVED["rhs_advective_kg_day"],
            "capillary_rhs_kg_day": OBSERVED["rhs_capillary_kg_day"],
            "actual_mass_dt_days": OBSERVED["actual_mass_dt_days"],
            "advective_only_mass_dt_days": OBSERVED["advective_only_mass_dt_days"],
            "capillary_only_mass_dt_days": OBSERVED["capillary_only_mass_dt_days"],
        }
        for field, expected in numeric.items():
            actual = float(summary[field])
            tol = max(1.0e-15, 1.0e-12 * max(abs(expected), 1.0))
            gate(
                f"R3R1R2_{field}_exact",
                abs(actual - expected) <= tol,
                actual,
            )

        gate(
            "R3R1R2_substeps_exact",
            int(summary["accepted_substeps_before_failure"])
            == OBSERVED["accepted_substeps_before_failure"],
            summary["accepted_substeps_before_failure"],
        )
        gate(
            "R3R1R2_terminal_pass_through_history_exact",
            int(summary["terminal_pass_through_activation_events_before_failure"])
            == OBSERVED["terminal_pass_through_events_before_failure"]
            and int(summary["terminal_pass_through_unique_streamlines_before_failure"])
            == OBSERVED["terminal_pass_through_unique_streamlines_before_failure"],
            {
                "events": summary[
                    "terminal_pass_through_activation_events_before_failure"
                ],
                "unique_streamlines": summary[
                    "terminal_pass_through_unique_streamlines_before_failure"
                ],
            },
        )
        gate(
            "R3R1R2_advection_dominance_decisive",
            abs(float(summary["advective_rhs_kg_day"]))
            > 1000.0 * abs(float(summary["capillary_rhs_kg_day"]))
            and float(summary["advective_only_mass_dt_days"])
            <= 1.001 * float(summary["actual_mass_dt_days"])
            and float(summary["capillary_only_mass_dt_days"])
            > 1.0e9 * float(summary["actual_mass_dt_days"]),
        )
        gate(
            "R3R1R2_design_handoff_exact",
            handoff_in["milestone"] == MILESTONE
            and handoff_in["authorized"] is True
            and handoff_in["execution"] is False
            and handoff_in["interior_repair_execution_authorized"] is False
            and handoff_in["F5_dataset_generation_authorized"] is False,
        )
        gate(
            "R3R1R2_no_repair_selected",
            decision_in["repair_selected"] is False
            and decision_in["interior_repair_executed"] is False
            and decision_in["terminal_pass_through_changed"] is False
            and decision_in["timestep_floor_changed"] is False
            and decision_in["mass_clipped_or_rescaled"] is False
            and decision_in["capacity_changed"] is False
            and decision_in["support_changed"] is False,
        )
        gate(
            "R3R1R2_diagnosis_internal_location_exact",
            diagnosis["limiting_interior_CV"]["streamline"] == OBSERVED["streamline"]
            and diagnosis["limiting_interior_CV"]["control_volume"]
            == OBSERVED["control_volume"]
            and diagnosis["limiting_interior_CV"]["bound"] == OBSERVED["bound"],
        )

        stage = "repair_selection_freeze"

        repair_selection = {
            "milestone": MILESTONE,
            "selected_repair_class": "event_triggered_same_time_flow_epoch_renewal",
            "selected_interior_face_limiter": False,
            "scientific_basis": {
                "localized_bound": OBSERVED["bound"],
                "localized_streamline": OBSERVED["streamline"],
                "localized_control_volume": OBSERVED["control_volume"],
                "driver": OBSERVED["classification"],
                "raw_internal_face_flux_is_shared_and_pairwise_conservative": True,
                "advective_mass_flux_definition": (
                    "F_face = q * local_Corey_fractional_flow(upwind_CV) * "
                    "gas_density(upwind_saturation, shared_face_pressure)"
                ),
                "capillary_mass_flux_is_single_shared_pairwise_face_flux": True,
                "interpretation": (
                    "The Day365 pressure/flow/streamline epoch has become stale "
                    "relative to the evolved saturation state. Since the raw internal "
                    "faces are already shared and conservative, the selected repair "
                    "renews the coupled flow epoch rather than modifying an interior face."
                ),
            },
            "explicitly_rejected_at_this_stage": [
                "interior advective face clipping",
                "pairwise interior flux redistribution",
                "reference-density substitution",
                "capillary weakening or removal",
                "timestep-floor relaxation",
                "component-mass clipping",
                "saturation clipping",
                "global mass rescaling",
                "capacity relaxation",
                "support expansion",
                "unlimited recursive automatic flow refresh",
            ],
        }

        trigger_contract = {
            "milestone": MILESTONE,
            "event_name": "INTERIOR_INVARIANT_DOMAIN_FLOW_EPOCH_RENEWAL",
            "event_time_day": EVENT_DAY,
            "elapsed_from_parent_day": OBSERVED["failure_elapsed_days"],
            "remaining_to_target_day": REMAINING_DAY,
            "trigger_condition": {
                "active_domain": "interior CVs 0..198",
                "bound": "UPPER_CAPACITY or LOWER_ZERO",
                "mass_bound_dt_at_or_below_frozen_MIN_TEACHER_DT": True,
                "ordinary_advective_CFL_must_remain_positive": True,
                "ordinary_capillary_CFL_must_remain_positive": True,
                "failed_substep_is_never_accepted": True,
            },
            "formal_control_event": {
                "streamline": OBSERVED["streamline"],
                "control_volume": OBSERVED["control_volume"],
                "bound": OBSERVED["bound"],
                "mass_fraction": OBSERVED["mass_fraction"],
                "saturation": OBSERVED["saturation"],
                "distance_to_bound_kg": OBSERVED["distance_to_bound_kg"],
            },
            "time_semantics": (
                "Mapback, pressure refresh, Darcy/Pollock/TOF regeneration, and "
                "reprojection are same-time operations with zero physical-time advance."
            ),
        }

        transfer_contract = {
            "milestone": MILESTONE,
            "same_time_pipeline": [
                "freeze exact last accepted 200-CV state at event time",
                "exact F4/E37A delta-CV mapback to full Cartesian event mass",
                "preserve exact Cartesian residual sidecar",
                "A2-E same-time pressure/mobility/EOS fixed-point refresh at fixed mass",
                "SG4 conservative Darcy flux regeneration",
                "SG5 exact Pollock retrace",
                "SG6 TOF/weight regeneration",
                "F4/E37A/SG7D bounded split-state reprojection on refreshed geometry",
                "rebuild all refreshed streamline-aligned transport fields and capacities",
                "resume remaining transport with unchanged F4 raw interior fluxes",
            ],
            "global_mass_invariant": (
                "Event Cartesian mass equals parent Cartesian mass plus accepted injection "
                "minus accepted corrected production. Same-time refresh/reprojection must "
                "preserve that event mass to frozen tolerances."
            ),
            "physical_time_advance_during_refresh_days": 0.0,
        }

        refreshed_epoch_contract = {
            "milestone": MILESTONE,
            "new_epoch_id": "DAY413P78677770818403_EVENT_REFRESH_01",
            "event_day": EVENT_DAY,
            "required_rebuilt_quantities": [
                "Cartesian saturation consistent with exact event mass and refreshed pressure",
                "Cartesian pressure",
                "saturation-dependent transmissibilities",
                "conservative Darcy face fluxes",
                "Pollock streamline XYZ",
                "streamline rate weights",
                "TOF coordinates and tau_end",
                "streamline-node pressure",
                "streamline-aligned porosity",
                "streamline-aligned permeability and anisotropy",
                "streamline-aligned nw/no/krw_max/kro_max",
                "200-CV geometry and pore volume",
                "200-CV pressure mass coefficient and capacity",
                "200-CV component mass and saturation",
                "exact residual-grid component-mass sidecar",
            ],
            "forbidden_epoch_mixing": [
                "new Pollock/TOF geometry with Day365 CV capacities",
                "new Pollock/TOF geometry with Day365 sampled pressure",
                "new Pollock/TOF geometry with Day365 constitutive CV fields",
                "new CV state with discarded or zeroed residual-grid mass",
            ],
        }

        execution_scope = {
            "milestone": MILESTONE,
            "prospective_execution_milestone": "POSTV16-AV4-F4-R3-R3",
            "maximum_event_refreshes_authorized": 1,
            "authorized_event_day": EVENT_DAY,
            "remaining_transport_days": REMAINING_DAY,
            "terminal_producer_pass_through": "preserved exactly on every flow epoch",
            "interior_raw_flux_operator": "preserved exactly",
            "minimum_teacher_dt": "unchanged",
            "if_second_interior_bound_conflict_occurs": (
                "scientific FAIL; no second automatic refresh"
            ),
        }

        proof_contract = {
            "milestone": MILESTONE,
            "R3R3_must_certify": [
                "event state equals exact last accepted R3 transport state",
                "failed R3 substep is not applied",
                "event mapback conserves accepted CV mass increment",
                "event Cartesian mass ledger closes",
                "same-time fixed-point refresh reconstructs identical event mass",
                "refreshed Darcy field is locally and globally conservative",
                "all refreshed Pollock streamlines are producer-captured",
                "refreshed TOF is finite positive and monotone",
                "bounded reprojection has zero overloaded CVs",
                "residual-grid mass remains nonnegative",
                "reprojection mass ledger closes",
                "refreshed streamline-aligned fields are rebuilt on refreshed geometry",
                "raw internal F4 advection/capillarity are unchanged",
                "F4-R2 terminal pass-through is unchanged",
                "physical time is unchanged across the refresh",
                "after one refresh either Day500 is reached or a second conflict is FAIL",
            ],
        }

        handoff = {
            "milestone": "POSTV16-AV4-F4-R3-R3",
            "name": (
                "Controlled First Event-Triggered Same-Time Flow-Epoch Renewal "
                "and Day500 Continuation Execution"
            ),
            "authorized": True,
            "execution": True,
            "required_R3R2_status": STATUS_PASS,
            "single_refresh_only": True,
            "allowed": [
                "reproduce the accepted trajectory to the first interior event",
                "bind exact R3-R1-R2 partial event state",
                "execute exact event-state mapback",
                "execute one same-time pressure/mobility fixed-point refresh",
                "recompute Darcy/Pollock/TOF and refreshed transport fields",
                "execute bounded same-time split-state reprojection",
                "resume transport with unchanged F4 raw internal operator",
                "retain frozen F4-R2 terminal producer pass-through",
                "continue to Day500 certification only if no second event occurs",
            ],
            "forbidden": [
                "interior face limiter or redistribution",
                "reference-density substitution",
                "capillary modification",
                "timestep-floor relaxation",
                "mass or saturation clipping",
                "global mass rescaling",
                "capacity relaxation",
                "support expansion",
                "second automatic event refresh",
                "model training",
                "checkpoint creation or inference",
                "locked OOD opening",
                "CMG",
            ],
            "F5_dataset_generation_authorized_now": False,
            "training_authorized": False,
            "A3_E2_authorized": False,
            "AV4_general_dynamic_transport_authorized": False,
        }

        decision = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "historical_F4_scientific_FAIL_preserved": True,
            "F4R3_scientific_FAIL_preserved": True,
            "R3R1R2_localization_bound": True,
            "selected_repair": "event_triggered_same_time_flow_epoch_renewal",
            "interior_face_limiter_selected": False,
            "pairwise_flux_redistribution_selected": False,
            "terminal_pass_through_changed": False,
            "raw_interior_transport_operator_changed": False,
            "timestep_floor_changed": False,
            "mass_clipped_or_rescaled": False,
            "capacity_changed": False,
            "support_changed": False,
            "repair_execution_performed": False,
            "physical_time_advanced": False,
            "mapback_executed": False,
            "flow_refresh_executed": False,
            "reprojection_executed": False,
            "R3R3_authorized": True,
            "R3R3_execution_authorized": True,
            "maximum_event_refreshes_authorized": 1,
            "F5_dataset_generation_authorized": False,
            "training_authorized": False,
            "A3_E2_authorized": False,
            "AV4_general_dynamic_transport_authorized": False,
        }

        summary_out = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "localized_event_day": EVENT_DAY,
            "remaining_days": REMAINING_DAY,
            "localized_streamline": OBSERVED["streamline"],
            "localized_control_volume": OBSERVED["control_volume"],
            "localized_bound": OBSERVED["bound"],
            "localized_driver": OBSERVED["classification"],
            "selected_repair": "event_triggered_same_time_flow_epoch_renewal",
            "interior_face_limiter_selected": False,
            "single_refresh_only": True,
            "repair_execution": False,
            "R3R3_authorized": True,
            "F5_authorized": False,
        }

        files = {
            "PAD_Stream_POSTV16_AV4_F4_R3_R2_Summary.json":
                json_bytes(summary_out),
            "POSTV16_AV4_F4_R3_R2_Repair_Selection_Contract.json":
                json_bytes(repair_selection),
            "POSTV16_AV4_F4_R3_R2_Event_Trigger_Contract.json":
                json_bytes(trigger_contract),
            "POSTV16_AV4_F4_R3_R2_Same_Time_Transfer_and_Refresh_Contract.json":
                json_bytes(transfer_contract),
            "POSTV16_AV4_F4_R3_R2_Refreshed_Flow_Epoch_Contract.json":
                json_bytes(refreshed_epoch_contract),
            "POSTV16_AV4_F4_R3_R2_Controlled_Execution_Scope.json":
                json_bytes(execution_scope),
            "POSTV16_AV4_F4_R3_R2_Prospective_Proof_Obligations.json":
                json_bytes(proof_contract),
            "POSTV16_AV4_F4_R3_R2_R3R3_Execution_Handoff_Contract.json":
                json_bytes(handoff),
            "POSTV16_AV4_F4_R3_R2_Decision_Contract.json":
                json_bytes(decision),
            "POSTV16_AV4_F4_R3_R2_Final_Gate_Matrix.csv":
                csv_bytes([{"gate": k, **v} for k, v in gates.items()]),
        }

        immutable_publish(out, files)

        manifest_rows = []
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name != "POSTV16_AV4_F4_R3_R2_Artifact_Manifest.csv":
                manifest_rows.append(
                    {"file": p.name, "sha256": sha256_file(p), "bytes": p.stat().st_size}
                )
        immutable_publish(
            out,
            {
                "POSTV16_AV4_F4_R3_R2_Artifact_Manifest.csv":
                    csv_bytes(manifest_rows)
            },
        )

        print()
        print("=" * 214)
        print(f"{MILESTONE}: EVENT-TRIGGERED FLOW-EPOCH RENEWAL DESIGN FREEZE PASS")
        print("=" * 214)
        print("Historical F4 scientific FAIL             : PRESERVED")
        print("F4-R3 scientific FAIL                     : PRESERVED")
        print("R3-R1-R2 localization                     : BOUND")
        print("Interior event day                        :", EVENT_DAY)
        print("Localized streamline / CV                 :", OBSERVED["streamline"], "/", OBSERVED["control_volume"])
        print("Mechanism                                 :", OBSERVED["classification"])
        print("Selected repair                           : same-time flow-epoch renewal")
        print("Interior face limiter selected            : False")
        print("Raw interior flux operator changed        : False")
        print("Terminal producer pass-through changed    : False")
        print("Maximum event refreshes authorized        : 1")
        print("Repair execution                          : False")
        print("POSTV16-AV4-F4-R3-R3                      : AUTHORIZED")
        print("F5 / training / A3-E2 / general AV4       : NOT AUTHORIZED")
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
            "historical_F4_scientific_FAIL_preserved": True,
            "F4R3_scientific_FAIL_preserved": True,
            "repair_execution_performed": False,
            "interior_face_limiter_selected": False,
            "physical_time_advanced": False,
            "mapback_executed": False,
            "flow_refresh_executed": False,
            "reprojection_executed": False,
            "R3R3_authorized": False,
            "F5_authorized": False,
            "training_authorized": False,
            "A3_E2_authorized": False,
            "AV4_general_dynamic_transport_authorized": False,
            "automatic_rerun_authorized": False,
        }
        data = json_bytes(report)
        p = blocked / "POSTV16_AV4_F4_R3_R2_Blocked_Report.json"
        if p.exists() and p.read_bytes() != data:
            p = blocked / (
                "POSTV16_AV4_F4_R3_R2_Blocked_Report_"
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
        print("NO EVENT REFRESH EXECUTION OR AUTOMATIC RERUN AUTHORIZED.")
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
