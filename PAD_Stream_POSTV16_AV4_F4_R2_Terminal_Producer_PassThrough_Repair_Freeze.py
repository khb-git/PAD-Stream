#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import subprocess
from pathlib import Path
from typing import Any


MILESTONE = "POSTV16-AV4-F4-R2"
PROTOCOL_ID = (
    "POSTV16_AV4_F4_R2_TERMINAL_PRODUCER_CAPACITY_PASSTHROUGH_"
    "BOUND_PRESERVING_TEACHER_REPAIR_DESIGN_FREEZE_V1"
)

STATUS_PASS = (
    "AV4F4R2_F4R1_ADVECTION_DOMINATED_TERMINAL_UPPER_CAPACITY_CONFLICT_BOUND_"
    "MINIMAL_PRODUCER_FACE_PASSTHROUGH_REPAIR_PROSPECTIVELY_FROZEN_"
    "NO_REPAIR_EXECUTION"
)
STATUS_BLOCKED = "AV4F4R2_REPAIR_DESIGN_FREEZE_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT_F4R1_COMMIT = "306a21b06726f16ef5afe96398f74bc6c4bc0d4e"

NCV = 200
TERMINAL_CV = 199
BACKGROUND = 0.20
INJECTED = 0.80

# Exact F4-R1 observed mechanism.
OBSERVED = {
    "accepted_substeps_before_failure": 1588,
    "elapsed_days": 17.87945060077662,
    "remaining_days": 117.12054939922338,
    "bound": "UPPER_CAPACITY",
    "streamline": 116,
    "control_volume": 199,
    "mass_fraction": 0.9999999999991409,
    "saturation": 0.7999999999995138,
    "distance_to_bound_kg": 3.475406629149802e-10,
    "rhs_total_kg_day": 2.3479210241911126,
    "rhs_advective_kg_day": 2.347949461711778,
    "rhs_capillary_kg_day": -2.8437520665240732e-05,
    "actual_mass_dt_days": 7.40102966271432e-11,
    "advective_only_mass_dt_days": 7.400940024100963e-11,
    "capillary_only_mass_dt_days": 1.0503753044378952,
    "classification": "ADVECTION_DOMINATED_BOUND_CONFLICT",
}

# --------------------------------------------------------------------------------------------------
# Exact source authorities.
# --------------------------------------------------------------------------------------------------

F4R1 = "PAD_Stream_POSTV16_AV4_F4_R1_Teacher_Stiffness_Failure_Localization.py"
F4R1_BLOB = "b3fc5722740992aeadfcbe7911cb9bf8d08027e5"

F4 = "PAD_Stream_POSTV16_AV4_F4_Day365_to_Day500_Restart_Teacher_Certification.py"
F4_BLOB = "a893ab32a1b3a396c3b2242f603c47bc94187a54"

F3 = "PAD_Stream_POSTV16_AV4_F3_Split_State_Restart_Model_and_Teacher_Protocol_Freeze.py"
F3_BLOB = "87b6cbf76272dfe3589b9f0da6559645f028be08"

F2R3 = "PAD_Stream_POSTV16_AV4_F2_R3_Bounded_Physical_Occupancy_Projection_Execution.py"
F2R3_BLOB = "359f3c0edf87e10bb4006cacdd271cd426fed22b"

E37A = "PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB = "0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"

E41R2 = "PAD_Stream_V16E41R2_Capacity_Aware_Conservative_MapBack_Timestep_Repair.py"
E41R2_BLOB = "f6961c48dc47c5fb55f2af658ef4ce429eb66533"

E41R3R1 = "PAD_Stream_V16E41R3R1_Accepted_Transition_Budget_Capacity_Limited_Regime_Audit.py"
E41R3R1_BLOB = "4c3438443513bd527b87e02a766634f5eebd2781"

SOURCE_BLOBS = {
    F4R1: F4R1_BLOB,
    F4: F4_BLOB,
    F3: F3_BLOB,
    F2R3: F2R3_BLOB,
    E37A: E37A_BLOB,
    E41R2: E41R2_BLOB,
    E41R3R1: E41R3R1_BLOB,
}

# --------------------------------------------------------------------------------------------------
# Formal Drive authority.
# --------------------------------------------------------------------------------------------------

BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

F4R1_REL = BASE_AV4 / "POSTV16_AV4_F4_R1_Teacher_Stiffness_Failure_Localization"
F4R1_SUMMARY = "PAD_Stream_POSTV16_AV4_F4_R1_Summary.json"
F4R1_DIAG = "POSTV16_AV4_F4_R1_Local_Limiter_and_Flux_Diagnosis.json"
F4R1_HANDOFF = "POSTV16_AV4_F4_R1_F4R2_Design_Handoff_Contract.json"
F4R1_DECISION = "POSTV16_AV4_F4_R1_Decision_Contract.json"
F4R1_STATE = "POSTV16_AV4_F4_R1_Partial_Teacher_State_at_Failure.npz"
F4R1_MANIFEST = "POSTV16_AV4_F4_R1_Artifact_Manifest.csv"
F4R1_STATUS = (
    "AV4F4R1_F4_TEACHER_STIFFNESS_SCIENTIFIC_FAIL_PRESERVED_"
    "LOCAL_BOUND_AND_FLUX_MECHANISM_DIAGNOSTICALLY_LOCALIZED_NO_REPAIR_SELECTED"
)

OUT_REL = BASE_AV4 / "POSTV16_AV4_F4_R2_Terminal_Producer_PassThrough_Repair_Freeze"
BLOCK_REL = BASE_AV4 / "POSTV16_AV4_F4_R2_BLOCKED"


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


def terminal_pass_through(
    *,
    mass: float,
    capacity: float,
    dt_days: float,
    advective_in_kg_day: float,
    raw_advective_out_kg_day: float,
    capillary_net_kg_day: float,
) -> dict[str, float | str | bool]:
    if not (
        math.isfinite(mass)
        and math.isfinite(capacity)
        and math.isfinite(dt_days)
        and math.isfinite(advective_in_kg_day)
        and math.isfinite(raw_advective_out_kg_day)
        and math.isfinite(capillary_net_kg_day)
    ):
        raise ValueError("nonfinite_terminal_pass_through_input")
    if capacity <= 0.0 or dt_days <= 0.0:
        raise ValueError("nonpositive_capacity_or_dt")
    if mass < 0.0 or mass > capacity:
        raise ValueError("parent_mass_outside_capacity")
    if advective_in_kg_day < 0.0 or raw_advective_out_kg_day < 0.0:
        raise ValueError("negative_positive_flow_advective_face")

    raw_rhs = (
        advective_in_kg_day
        - raw_advective_out_kg_day
        + capillary_net_kg_day
    )
    raw_trial = mass + dt_days * raw_rhs

    corrected_out = raw_advective_out_kg_day
    active_bound = "NONE"

    if raw_trial > capacity:
        active_bound = "UPPER_CAPACITY"
        corrected_out = (
            advective_in_kg_day
            + capillary_net_kg_day
            - (capacity - mass) / dt_days
        )
    elif raw_trial < 0.0:
        active_bound = "LOWER_ZERO"
        corrected_out = (
            advective_in_kg_day
            + capillary_net_kg_day
            + mass / dt_days
        )

    if corrected_out < 0.0:
        return {
            "feasible": False,
            "active_bound": active_bound,
            "raw_trial_mass_kg": raw_trial,
            "corrected_outflow_kg_day": corrected_out,
            "corrected_trial_mass_kg": float("nan"),
            "correction_kg_day": corrected_out - raw_advective_out_kg_day,
        }

    corrected_rhs = (
        advective_in_kg_day
        - corrected_out
        + capillary_net_kg_day
    )
    corrected_trial = mass + dt_days * corrected_rhs

    return {
        "feasible": True,
        "active_bound": active_bound,
        "raw_trial_mass_kg": raw_trial,
        "corrected_outflow_kg_day": corrected_out,
        "corrected_trial_mass_kg": corrected_trial,
        "correction_kg_day": corrected_out - raw_advective_out_kg_day,
    }


def self_test() -> None:
    # Upper-bound pass-through: excess incoming mass becomes extra production.
    x = terminal_pass_through(
        mass=9.99,
        capacity=10.0,
        dt_days=0.1,
        advective_in_kg_day=5.0,
        raw_advective_out_kg_day=4.0,
        capillary_net_kg_day=0.0,
    )
    assert x["feasible"] is True
    assert x["active_bound"] == "UPPER_CAPACITY"
    assert abs(float(x["corrected_trial_mass_kg"]) - 10.0) < 1.0e-14
    assert abs(float(x["corrected_outflow_kg_day"]) - 4.9) < 1.0e-14

    # Feasible raw step is bitwise conceptually unchanged.
    y = terminal_pass_through(
        mass=5.0,
        capacity=10.0,
        dt_days=0.1,
        advective_in_kg_day=2.0,
        raw_advective_out_kg_day=2.0,
        capillary_net_kg_day=0.0,
    )
    assert y["active_bound"] == "NONE"
    assert float(y["correction_kg_day"]) == 0.0
    assert float(y["corrected_outflow_kg_day"]) == 2.0

    # Global one-cell ledger: delta storage = dt*(injection-production).
    dx = float(x["corrected_trial_mass_kg"]) - 9.99
    ledger = dx - 0.1 * (5.0 - float(x["corrected_outflow_kg_day"]))
    assert abs(ledger) < 1.0e-14

    print(
        "POSTV16-AV4-F4-R2 terminal producer pass-through "
        "repair-design self-test: PASS"
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
        "POSTV16-AV4-F4-R2 — TERMINAL PRODUCER CAPACITY-PASS-THROUGH "
        "BOUND-PRESERVING TEACHER REPAIR DESIGN FREEZE"
    )
    print("=" * 214)
    print("DESIGN / FREEZE ONLY.")
    print("F4 SCIENTIFIC FAIL AND F4-R1 LOCALIZATION REMAIN IMMUTABLE.")
    print("NO TEACHER REPAIR EXECUTION. NO TIMESTEP FLOOR RELAXATION.")
    print("NO INTERIOR FACE MODIFICATION. NO CAPILLARY MODIFICATION.")
    print("NO EOS/DENSITY REPLACEMENT. NO CLIPPING. NO RESCALING. NO SUPPORT CHANGE.")
    print("NO MAPBACK. NO DAY500 REFRESH. NO REPROJECTION. NO TRAINING. NO CMG.")
    print()

    try:
        # ------------------------------------------------------------------------------------------
        # Repository/source authority.
        # ------------------------------------------------------------------------------------------
        stage = "repository_authority"

        parent = git_text(root, "rev-parse", "HEAD^")
        status = git_text(root, "status", "--porcelain")

        gate(
            "repository_parent_is_F4R1_commit",
            parent == PARENT_F4R1_COMMIT,
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

        # ------------------------------------------------------------------------------------------
        # Bind formal F4-R1 PASS and exact observed mechanism.
        # ------------------------------------------------------------------------------------------
        stage = "F4R1_localization_binding"

        r1d = drive / F4R1_REL
        gate("F4R1_output_present", r1d.is_dir(), str(r1d))
        manifest = verify_manifest(r1d, F4R1_MANIFEST)
        gate("F4R1_manifest_exact_8", len(manifest) == 8, len(manifest))
        gate("F4R1_state_manifested", F4R1_STATE in manifest, F4R1_STATE)

        summary = load_json(r1d / F4R1_SUMMARY)
        diag = load_json(r1d / F4R1_DIAG)
        handoff_r1 = load_json(r1d / F4R1_HANDOFF)
        decision_r1 = load_json(r1d / F4R1_DECISION)

        gate(
            "F4R1_status_exact",
            summary["status"] == F4R1_STATUS,
            summary["status"],
        )
        gate(
            "F4R1_formal_F4_fail_preserved",
            summary["F4_scientific_FAIL_preserved"] is True
            and diag["F4_scientific_FAIL_preserved"] is True,
        )
        gate(
            "F4R1_mechanism_exact",
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

        numeric_fields = [
            "failure_elapsed_days",
            "failure_remaining_days",
            "limiter_mass_fraction",
            "limiter_saturation",
            "limiter_distance_to_bound_kg",
            "total_rhs_kg_day",
            "advective_rhs_kg_day",
            "capillary_rhs_kg_day",
            "actual_mass_dt_days",
            "advective_only_mass_dt_days",
            "capillary_only_mass_dt_days",
        ]
        expected_lookup = {
            "failure_elapsed_days": OBSERVED["elapsed_days"],
            "failure_remaining_days": OBSERVED["remaining_days"],
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
        for field in numeric_fields:
            actual = float(summary[field])
            expected = float(expected_lookup[field])
            tol = max(1.0e-15, 1.0e-12 * max(abs(expected), 1.0))
            gate(
                f"F4R1_{field}_exact",
                abs(actual - expected) <= tol,
                actual,
            )

        gate(
            "F4R1_substeps_exact",
            int(summary["accepted_substeps_before_failure"])
            == OBSERVED["accepted_substeps_before_failure"],
            summary["accepted_substeps_before_failure"],
        )
        gate(
            "F4R1_advection_dominance_decisive",
            abs(float(summary["advective_rhs_kg_day"]))
            > 1000.0 * abs(float(summary["capillary_rhs_kg_day"]))
            and float(summary["advective_only_mass_dt_days"])
            <= 1.0001 * float(summary["actual_mass_dt_days"])
            and float(summary["capillary_only_mass_dt_days"])
            > 1.0e9 * float(summary["actual_mass_dt_days"]),
            {
                "advective_RHS": summary["advective_rhs_kg_day"],
                "capillary_RHS": summary["capillary_rhs_kg_day"],
                "adv_only_dt": summary["advective_only_mass_dt_days"],
                "cap_only_dt": summary["capillary_only_mass_dt_days"],
            },
        )
        gate(
            "F4R1_terminal_CV_conflict_exact",
            int(summary["limiter_control_volume"]) == TERMINAL_CV,
            summary["limiter_control_volume"],
        )
        gate(
            "F4R1_R2_design_handoff_exact",
            handoff_r1["milestone"] == MILESTONE
            and handoff_r1["authorized"] is True
            and handoff_r1["execution"] is False
            and handoff_r1["teacher_repair_execution_authorized"] is False
            and handoff_r1["F5_dataset_generation_authorized"] is False,
            handoff_r1,
        )
        gate(
            "F4R1_no_repair_selected",
            decision_r1["repair_selected"] is False
            and decision_r1["teacher_repair_executed"] is False
            and decision_r1["timestep_floor_changed"] is False
            and decision_r1["mass_clipped_or_rescaled"] is False
            and decision_r1["capacity_changed"] is False
            and decision_r1["support_changed"] is False,
        )

        # ------------------------------------------------------------------------------------------
        # Freeze the repair choice.
        # ------------------------------------------------------------------------------------------
        stage = "repair_choice_freeze"

        repair = {
            "milestone": MILESTONE,
            "candidate_count": 1,
            "selected_candidate": (
                "minimal_terminal_producer_face_capacity_pass_through"
            ),
            "scientific_basis": {
                "localized_control_volume": "terminal CV j=199",
                "localized_bound": "UPPER_CAPACITY",
                "localized_driver": "ADVECTION_DOMINATED_BOUND_CONFLICT",
                "evidence": {
                    "mass_fraction": OBSERVED["mass_fraction"],
                    "distance_to_upper_capacity_kg": OBSERVED[
                        "distance_to_bound_kg"
                    ],
                    "total_RHS_kg_day": OBSERVED["rhs_total_kg_day"],
                    "advective_RHS_kg_day": OBSERVED[
                        "rhs_advective_kg_day"
                    ],
                    "capillary_RHS_kg_day": OBSERVED[
                        "rhs_capillary_kg_day"
                    ],
                    "raw_mass_limiter_dt_days": OBSERVED[
                        "actual_mass_dt_days"
                    ],
                    "capillary_only_mass_dt_days": OBSERVED[
                        "capillary_only_mass_dt_days"
                    ],
                },
            },
            "preserved_raw_physics": [
                "F4 local-density positive-flow advective mass flux on every inlet and internal face",
                "F4 source-authentic spatial-Corey fractional flow",
                "F4 pairwise internal capillary mass flux",
                "zero capillary boundary mass flux",
                "fixed rate-controlled injector component-mass source",
                "F4 E37A CV capacities and mass-to-saturation relation",
                "F3 200-CV / 17-channel restart signature",
            ],
            "explicitly_not_selected": [
                "replace local-density advection with reference-density advection",
                "global or internal-face flux optimization",
                "general interior invariant-domain redistribution",
                "capillary weakening or removal",
                "saturation clipping",
                "component-mass clipping",
                "global mass rescaling",
                "capacity relaxation",
                "support-domain expansion",
                "timestep-floor relaxation",
                "automatic pressure/flow refresh inside the frozen parent-geometry substep",
            ],
            "scope_of_correction": {
                "modified_face": "external producer face only, index 200",
                "internal_advective_faces_modified": False,
                "injector_face_modified": False,
                "capillary_faces_modified": False,
                "EOS_or_density_law_modified": False,
            },
        }

        # ------------------------------------------------------------------------------------------
        # Freeze exact pass-through algebra and proof obligations.
        # ------------------------------------------------------------------------------------------
        stage = "pass_through_algebra_freeze"

        algebra = {
            "milestone": MILESTONE,
            "notation": {
                "M": "terminal CV component mass at start of substep",
                "C": "frozen E37A terminal CV component-mass capacity",
                "h": "accepted substep duration in days",
                "Ain": "raw advective component-mass flux into terminal CV",
                "Aout_raw": "raw advective component-mass producer outflow",
                "Knet": (
                    "capillary west-face inflow minus terminal capillary outflow; "
                    "terminal capillary outflow remains exactly zero"
                ),
            },
            "raw_trial": "M_raw = M + h*(Ain - Aout_raw + Knet)",
            "upper_bound_correction": {
                "activation": "M_raw > C",
                "corrected_outflow": (
                    "Aout_star = Ain + Knet - (C-M)/h"
                ),
                "equivalent_minimal_increment": (
                    "Aout_star = Aout_raw + (M_raw-C)/h"
                ),
                "result": "M_star = C exactly",
            },
            "lower_bound_correction": {
                "activation": "M_raw < 0",
                "corrected_outflow": (
                    "Aout_star = Ain + Knet + M/h"
                ),
                "equivalent_minimal_decrement": (
                    "Aout_star = Aout_raw + M_raw/h"
                ),
                "result": "M_star = 0 exactly",
                "feasibility_requirement": "Aout_star >= 0",
                "on_infeasible": "scientific FAIL; no clipping or alternate repair",
            },
            "inactive_case": {
                "activation": "0 <= M_raw <= C",
                "corrected_outflow": "Aout_star = Aout_raw exactly",
            },
            "production_ledger": (
                "substep produced component mass uses Aout_star*h, never the raw "
                "outlet flux when the pass-through correction activates"
            ),
            "global_telescoping_ledger": (
                "sum(M_new)-sum(M_old) = h*(sum injector advective mass flux - "
                "sum corrected producer advective mass flux); capillary boundary "
                "flux is identically zero"
            ),
            "minimality": (
                "only the external producer face is changed, by exactly the amount "
                "needed to place the terminal CV on the violated physical bound"
            ),
        }

        timestep = {
            "milestone": MILESTONE,
            "substep_rule": (
                "h = min(remaining, advective_CFL_dt, capillary_CFL_dt, "
                "interior_mass_bound_dt)"
            ),
            "interior_mass_bound_domain": "CV indices 0..198 only",
            "terminal_mass_bound_dt_removed_from_global_limiter": True,
            "terminal_bound_enforcement": (
                "algebraic producer-face pass-through after raw face construction "
                "and before the mass update"
            ),
            "original_F4_MIN_TEACHER_DT_DAYS_unchanged": True,
            "if_interior_mass_dt_below_minimum": (
                "scientific FAIL — interior bound conflict after targeted terminal repair"
            ),
            "if_terminal_corrected_outflow_negative": (
                "scientific FAIL — terminal pass-through infeasible"
            ),
            "no_timestep_floor_relaxation": True,
        }

        proof = {
            "milestone": MILESTONE,
            "prospective_invariants_R3_must_certify": [
                {
                    "name": "identity_when_raw_terminal_step_feasible",
                    "statement": (
                        "if 0<=M_raw<=C then Aout_star equals Aout_raw exactly"
                    ),
                },
                {
                    "name": "terminal_bound_preservation",
                    "statement": "0 <= M_terminal_new <= C_terminal every accepted step",
                },
                {
                    "name": "interior_operator_identity",
                    "statement": (
                        "all inlet/internal advective faces and all capillary faces "
                        "are bitwise/numerically identical to the frozen F4 raw operator"
                    ),
                },
                {
                    "name": "internal_pairwise_conservation",
                    "statement": (
                        "each unchanged internal face remains one cell's outflow and "
                        "the adjacent cell's inflow"
                    ),
                },
                {
                    "name": "global_component_mass_conservation",
                    "statement": (
                        "storage change equals fixed injector mass minus corrected "
                        "producer mass to numerical roundoff"
                    ),
                },
                {
                    "name": "no_posthoc_state_edit",
                    "statement": (
                        "no mass/saturation clipping, rescaling, capacity relaxation, "
                        "or support modification occurs"
                    ),
                },
                {
                    "name": "localized_repair_only",
                    "statement": (
                        "a correction may occur only on terminal producer faces whose "
                        "raw CFL-safe trial violates a physical mass bound"
                    ),
                },
            ],
            "strong_form_consistency": (
                "the frozen F4 raw strong-form mass flux is preserved exactly everywhere "
                "the terminal invariant-domain constraint is inactive; the correction is "
                "an external boundary closure, not an interior constitutive rewrite"
            ),
        }

        # Numerical algebra sanity check using the observed limiting state with
        # an ordinary CFL-safe dt. We do not execute the teacher.
        probe_dt = min(
            0.5 * 0.017929627892948993,
            0.5 * 0.012827525897157238,
        )
        # Reconstruct capacity from observed room and mass fraction:
        # room = C*(1-f), so C = room/(1-f).
        one_minus_f = 1.0 - OBSERVED["mass_fraction"]
        capacity_probe = (
            OBSERVED["distance_to_bound_kg"] / one_minus_f
            if one_minus_f > 0.0
            else float("inf")
        )
        mass_probe = OBSERVED["mass_fraction"] * capacity_probe

        # We know net advective RHS, not the individual faces. A synthetic split
        # with the exact observed divergence is sufficient to prove the algebra.
        raw_out_probe = 100.0
        adv_in_probe = raw_out_probe + OBSERVED["rhs_advective_kg_day"]
        cap_net_probe = OBSERVED["rhs_capillary_kg_day"]

        probe = terminal_pass_through(
            mass=mass_probe,
            capacity=capacity_probe,
            dt_days=probe_dt,
            advective_in_kg_day=adv_in_probe,
            raw_advective_out_kg_day=raw_out_probe,
            capillary_net_kg_day=cap_net_probe,
        )
        gate(
            "observed_upper_capacity_probe_activates",
            probe["feasible"] is True
            and probe["active_bound"] == "UPPER_CAPACITY",
            probe,
        )
        gate(
            "observed_upper_capacity_probe_lands_on_bound",
            abs(
                float(probe["corrected_trial_mass_kg"])
                - capacity_probe
            )
            <= max(1.0e-10, 1.0e-12 * capacity_probe),
            {
                "corrected_mass": probe["corrected_trial_mass_kg"],
                "capacity": capacity_probe,
            },
        )
        gate(
            "observed_probe_requires_increased_production",
            float(probe["correction_kg_day"]) > 0.0,
            probe["correction_kg_day"],
        )

        # ------------------------------------------------------------------------------------------
        # Freeze controlled execution handoff.
        # ------------------------------------------------------------------------------------------
        stage = "F4R3_handoff_freeze"

        handoff = {
            "milestone": "POSTV16-AV4-F4-R3",
            "name": (
                "Controlled Terminal Producer Capacity-Pass-Through "
                "Restart-Teacher Repair Execution"
            ),
            "authorized": True,
            "execution": True,
            "required_R2_status": STATUS_PASS,
            "single_candidate_only": True,
            "required_repair": (
                "minimal_terminal_producer_face_capacity_pass_through"
            ),
            "allowed": [
                "re-execute the F4 Day365->Day500 validation teacher from the exact Day365 parent",
                "use the unchanged F4 raw advection and capillary face construction",
                "compute the F4 advection/capillary CFL timesteps unchanged",
                "apply the original mass-bound timestep limiter to interior CVs 0..198 only",
                "apply the frozen algebraic pass-through only to external producer faces",
                "accumulate production using the corrected producer mass flux",
                "certify every R2 invariant and repair diagnostic",
                "if the repaired teacher completes, continue the original F4 E37A mapback, Day500 flow refresh, and bounded reprojection",
            ],
            "scientific_fail_conditions": [
                "interior CV mass-bound timestep collapses below the unchanged F4 minimum",
                "terminal lower-bound correction requires negative producer mass outflow",
                "any accepted CV mass leaves [0,C] beyond numerical roundoff",
                "global component-mass ledger fails",
                "any inlet/internal advective face changes from frozen F4 raw physics",
                "any capillary face changes from frozen F4 physics",
                "E37A mapback failure",
                "Day500 flow/Pollock/TOF refresh failure",
                "Day500 bounded reprojection failure",
            ],
            "forbidden": [
                "reference-density substitution for F4 local-density advective flux",
                "interior face flux limiting or optimization",
                "capillary tuning",
                "timestep-floor relaxation",
                "mass or saturation clipping",
                "global mass rescaling",
                "capacity relaxation",
                "support expansion",
                "model training",
                "checkpoint creation or inference",
                "locked-OOD opening",
                "CMG",
            ],
            "F5_dataset_generation_authorized_now": False,
            "training_authorized": False,
            "A3_E2_authorized": False,
            "AV4_dynamic_transport_execution_authorized": False,
        }

        decision = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "F4_scientific_FAIL_preserved": True,
            "F4R1_localization_bound": True,
            "mechanism": OBSERVED["classification"],
            "repair_candidate_count": 1,
            "selected_repair": (
                "minimal_terminal_producer_face_capacity_pass_through"
            ),
            "repair_execution_performed": False,
            "interior_advective_operator_changed": False,
            "capillary_operator_changed": False,
            "EOS_or_density_law_changed": False,
            "timestep_floor_changed": False,
            "mass_clipped_or_rescaled": False,
            "capacity_changed": False,
            "support_changed": False,
            "F4R3_authorized": True,
            "F4R3_execution_authorized": True,
            "F5_dataset_generation_authorized": False,
            "training_authorized": False,
            "A3_E2_authorized": False,
            "AV4_dynamic_transport_execution_authorized": False,
        }

        summary_out = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "protocol_id": PROTOCOL_ID,
            "F4_scientific_FAIL_preserved": True,
            "F4R1_classification": OBSERVED["classification"],
            "F4R1_limiter_bound": OBSERVED["bound"],
            "F4R1_limiter_location": [
                OBSERVED["streamline"],
                OBSERVED["control_volume"],
            ],
            "selected_repair": (
                "minimal_terminal_producer_face_capacity_pass_through"
            ),
            "modified_face_scope": "external_producer_face_only",
            "interior_advective_faces_changed": False,
            "capillary_faces_changed": False,
            "EOS_or_density_law_changed": False,
            "timestep_floor_changed": False,
            "repair_execution": False,
            "F4R3_authorized": True,
            "F5_authorized": False,
        }

        files = {
            "PAD_Stream_POSTV16_AV4_F4_R2_Summary.json":
                json_bytes(summary_out),
            "POSTV16_AV4_F4_R2_Repair_Selection_Contract.json":
                json_bytes(repair),
            "POSTV16_AV4_F4_R2_Terminal_PassThrough_Algebra_Contract.json":
                json_bytes(algebra),
            "POSTV16_AV4_F4_R2_Timestep_and_Invariant_Domain_Contract.json":
                json_bytes(timestep),
            "POSTV16_AV4_F4_R2_Prospective_Proof_Obligations.json":
                json_bytes(proof),
            "POSTV16_AV4_F4_R2_F4R3_Execution_Handoff_Contract.json":
                json_bytes(handoff),
            "POSTV16_AV4_F4_R2_Decision_Contract.json":
                json_bytes(decision),
            "POSTV16_AV4_F4_R2_Final_Gate_Matrix.csv":
                csv_bytes(
                    [{"gate": name, **value} for name, value in gates.items()]
                ),
        }

        immutable_publish(out, files)

        manifest_rows = []
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name != "POSTV16_AV4_F4_R2_Artifact_Manifest.csv":
                manifest_rows.append(
                    {
                        "file": p.name,
                        "sha256": sha256_file(p),
                        "bytes": p.stat().st_size,
                    }
                )
        immutable_publish(
            out,
            {
                "POSTV16_AV4_F4_R2_Artifact_Manifest.csv":
                    csv_bytes(manifest_rows)
            },
        )

        print()
        print("=" * 214)
        print(f"{MILESTONE}: TERMINAL PRODUCER PASS-THROUGH REPAIR DESIGN FREEZE PASS")
        print("=" * 214)
        print("F4 scientific FAIL                         : PRESERVED")
        print("F4-R1 mechanism                           :", OBSERVED["classification"])
        print("Localized CV                              :", OBSERVED["streamline"], "/", OBSERVED["control_volume"])
        print("Selected repair                           : terminal producer pass-through")
        print("Interior advective faces modified         : False")
        print("Capillary faces modified                  : False")
        print("EOS / density law modified                : False")
        print("Timestep floor modified                   : False")
        print("Repair execution                          : False")
        print("POSTV16-AV4-F4-R3                         : AUTHORIZED")
        print("F5 / training / A3-E2 / dynamic AV4       : NOT AUTHORIZED")
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
            "F4_scientific_FAIL_preserved": True,
            "F4R1_localization_preserved": True,
            "repair_execution_performed": False,
            "F4R3_authorized": False,
            "F5_authorized": False,
            "training_authorized": False,
            "A3_E2_authorized": False,
            "AV4_dynamic_transport_execution_authorized": False,
            "automatic_rerun_authorized": False,
        }
        data = json_bytes(report)
        p = blocked / "POSTV16_AV4_F4_R2_Blocked_Report.json"
        if p.exists() and p.read_bytes() != data:
            p = blocked / (
                "POSTV16_AV4_F4_R2_Blocked_Report_"
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
        print("F4 scientific FAIL and F4-R1 localization remain immutable.")
        print("NO REPAIR EXECUTION OR AUTOMATIC RERUN AUTHORIZED.")
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
