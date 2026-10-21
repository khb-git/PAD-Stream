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

import numpy as np


MILESTONE = "POSTV16-AV4-F2-R2"

PROTOCOL_ID = (
    "POSTV16_AV4_F2_R2_BOUNDED_PHYSICAL_OCCUPANCY_SPLIT_STATE_"
    "GRID_TO_REFRESHED_STREAMLINE_PARENT_PROJECTION_FREEZE_V1"
)

STATUS_PASS = (
    "AV4F2R2_F2R1_CAPACITY_LOCALIZATION_BOUND_SINGLE_BOUNDED_PHYSICAL_"
    "OCCUPANCY_SPLIT_STATE_PARENT_PROJECTION_PROSPECTIVELY_FROZEN_"
    "NO_REPAIR_EXECUTION"
)

STATUS_BLOCKED = "AV4F2R2_PROTOCOL_FREEZE_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT_F2R1_COMMIT = "1e2c253e263cb14a515ebad8758a80ecc3eb6ee1"

GRID = (15, 50, 50)
NSL = 1078
NN = 201
NCV = 200

# --------------------------------------------------------------------------------------------------
# Exact repository authorities.
# --------------------------------------------------------------------------------------------------

F2R1 = "PAD_Stream_POSTV16_AV4_F2_R1_CV_Capacity_Failure_Localization.py"
F2R1_BLOB = "f8cb7c9ed63fa4610f3c24e7fed8f17bbaf5f14a"

F2 = "PAD_Stream_POSTV16_AV4_F2_Controlled_Day365_Conservative_Parent_State_Projection.py"
F2_BLOB = "0f286a834b1cb2306403a9b9fa76b38841a31a11"

F1R2 = (
    "PAD_Stream_POSTV16_AV4_F1_R2_Corrected_Restart_State_and_"
    "Conservative_Parent_Projection_Freeze.py"
)
F1R2_BLOB = "51f86f3591bf66148ef468b304c18fb4fc668e77"

A2E = "PAD_Stream_POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution.py"
A2E_BLOB = "79a8969233b72b4543edd382a0c3d1028c6dca09"

R2 = "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"

E37A = "PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB = "0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"

SG7D = "PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"
SG7D_BLOB = "890088c0c0fcab415a2c7351c5079ca8ee12bf82"

AV1_R7R2 = (
    "PAD_Stream_POSTV16_AV1_D_R7_R2_"
    "Conservative_Bounded_Overlap_Occupancy_Reconciliation_Freeze.py"
)
AV1_R7R2_BLOB = "c9c4ceed05e6e631ad071b9da901d35874609255"

SOURCE_BLOBS = {
    F2R1: F2R1_BLOB,
    F2: F2_BLOB,
    F1R2: F1R2_BLOB,
    A2E: A2E_BLOB,
    R2: R2_BLOB,
    E37A: E37A_BLOB,
    SG7D: SG7D_BLOB,
    AV1_R7R2: AV1_R7R2_BLOB,
}

# --------------------------------------------------------------------------------------------------
# Formal Drive authorities.
# --------------------------------------------------------------------------------------------------

BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

F2R1_REL = BASE_AV4 / "POSTV16_AV4_F2_R1_CV_Capacity_Failure_Localization"
F2R1_SUMMARY = "PAD_Stream_POSTV16_AV4_F2_R1_Summary.json"
F2R1_DIAG = "POSTV16_AV4_F2_R1_Capacity_Mechanism_Diagnosis.json"
F2R1_HANDOFF = "POSTV16_AV4_F2_R1_F2R2_Design_Handoff_Contract.json"
F2R1_DECISION = "POSTV16_AV4_F2_R1_Decision_Contract.json"
F2R1_MANIFEST = "POSTV16_AV4_F2_R1_Artifact_Manifest.csv"
F2R1_STATUS = (
    "AV4F2R1_F2_CV_CAPACITY_SCIENTIFIC_FAIL_PRESERVED_LOCALIZED_"
    "NORMALIZED_TRANSPOSE_PROJECTION_GEOMETRY_AND_CAPACITY_MECHANISM_"
    "DIAGNOSED_NO_REPAIR_SELECTED"
)

OUT_REL = BASE_AV4 / "POSTV16_AV4_F2_R2_Bounded_Physical_Occupancy_Projection_Freeze"
BLOCK_REL = BASE_AV4 / "POSTV16_AV4_F2_R2_BLOCKED"


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


def near(a: float, b: float, rtol: float = 1.0e-12, atol: float = 1.0e-9) -> bool:
    return abs(float(a) - float(b)) <= max(
        atol,
        rtol * max(abs(float(b)), 1.0),
    )


def self_test() -> None:
    # Two cells:
    # cell 0 under-covered: W=4, physical PV=10 -> 40% mapped, 60% residual
    # cell 1 over-covered: W=6, physical PV=4 -> 100% mapped, normalized by W
    parent = np.asarray([12.0, 8.0], dtype=np.float64)
    cell_pv = np.asarray([10.0, 4.0], dtype=np.float64)
    flat = np.asarray([0, 0, 1, 1], dtype=np.int64)
    pv_q = np.asarray([1.0, 3.0, 2.0, 4.0], dtype=np.float64)

    W = np.bincount(flat, weights=pv_q, minlength=2)
    denom = np.maximum(cell_pv, W)
    sub_mass = parent[flat] * pv_q / denom[flat]
    mapped_cell = np.bincount(flat, weights=sub_mass, minlength=2)
    residual = parent - mapped_cell

    assert np.allclose(W, [4.0, 6.0])
    assert np.allclose(mapped_cell, [4.8, 8.0])
    assert np.allclose(residual, [7.2, 0.0])
    assert np.all(residual >= -1.0e-14)
    assert abs(float(np.sum(mapped_cell + residual)) - float(np.sum(parent))) < 1.0e-14

    # Bounded operator can never exceed the pure physical-PV comparator edgewise.
    diag = parent[flat] * pv_q / cell_pv[flat]
    assert np.all(sub_mass <= diag + 1.0e-14)

    print(
        "POSTV16-AV4-F2-R2 bounded physical-occupancy projection "
        "protocol self-test: PASS"
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
        "POSTV16-AV4-F2-R2 — BOUNDED PHYSICAL-OCCUPANCY SPLIT-STATE "
        "PARENT-PROJECTION PROTOCOL FREEZE"
    )
    print("=" * 214)
    print("DESIGN / FREEZE ONLY.")
    print("F2 SCIENTIFIC FAIL AND F2-R1 LOCALIZATION REMAIN IMMUTABLE.")
    print("NO PROJECTION REPAIR EXECUTION. NO SUPPORT EXPANSION. NO LP EXECUTION.")
    print("NO CLIPPING. NO GLOBAL RESCALING. NO SATURATION-BOUND RELAXATION.")
    print("NO TEACHER. NO MODEL INFERENCE. NO TIME ADVANCE. NO MAPBACK. NO TRAINING. NO CMG.")
    print()

    try:
        # ------------------------------------------------------------------------------------------
        # Repository authority.
        # ------------------------------------------------------------------------------------------
        stage = "repository_authority"

        parent = git_text(root, "rev-parse", "HEAD^")
        status = git_text(root, "status", "--porcelain")

        gate(
            "repository_parent_is_F2R1_commit",
            parent == PARENT_F2R1_COMMIT,
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
        # Bind formal F2-R1 localization PASS.
        # ------------------------------------------------------------------------------------------
        stage = "F2R1_localization_binding"

        d = drive / F2R1_REL
        gate("F2R1_output_present", d.is_dir(), str(d))
        m = verify_manifest(d, F2R1_MANIFEST)
        gate("F2R1_manifest_exact_8", len(m) == 8, len(m))

        s = load_json(d / F2R1_SUMMARY)
        q = load_json(d / F2R1_DIAG)
        h = load_json(d / F2R1_HANDOFF)
        dec = load_json(d / F2R1_DECISION)

        gate("F2R1_status_exact", s["status"] == F2R1_STATUS, s["status"])
        gate("F2R1_F2_fail_preserved", dec["F2_scientific_FAIL_preserved"] is True)
        gate("F2R1_repair_not_selected", dec["repair_selected"] is False)
        gate(
            "F2R1_failure_population_exact",
            int(s["overloaded_CV_count"]) == 32919
            and int(s["worst_streamline"]) == 849
            and int(s["worst_control_volume"]) == 157,
            {
                "overloaded_CV_count": s["overloaded_CV_count"],
                "worst": [s["worst_streamline"], s["worst_control_volume"]],
            },
        )
        gate(
            "F2R1_worst_capacity_ratio_exact",
            near(
                float(s["worst_target_to_capacity_ratio"]),
                13.858758582726606,
                rtol=1.0e-12,
            ),
            s["worst_target_to_capacity_ratio"],
        )
        gate(
            "F2R1_global_capacity_sufficient",
            s["global_CV_capacity_sufficient_for_total_S0_mass"] is True,
        )
        gate(
            "F2R1_physicalPV_comparator_zero_overloads",
            int(s["physicalPV_sampling_comparator_overloaded_CV_count"]) == 0,
            s["physicalPV_sampling_comparator_overloaded_CV_count"],
        )
        gate(
            "F2R1_mechanism_classification_exact",
            q["mechanism_interpretation"]["mass_conservation_failure"] is False
            and q["mechanism_interpretation"]["A2E_parent_state_failure"] is False
            and q["mechanism_interpretation"]["SG7D_geometry_failure"] is False
            and q["mechanism_interpretation"]["E37A_capacity_definition_failure"] is False
            and q["mechanism_interpretation"]["F2_normalized_transpose_local_capacity_incompatibility"] is True
            and q["mechanism_interpretation"]["local_assignment_incompatibility_proven"] is True,
        )
        gate(
            "F2R1_design_only_handoff_exact",
            h["milestone"] == MILESTONE
            and h["authorized"] is True
            and h["execution"] is False
            and h["F2_repair_execution_authorized"] is False
            and h["F3_authorized"] is False
            and h["A3_E2_authorized"] is False
            and h["AV4_dynamic_transport_execution_authorized"] is False,
            h,
        )

        # ------------------------------------------------------------------------------------------
        # Freeze one bounded physical-occupancy candidate.
        # ------------------------------------------------------------------------------------------
        stage = "single_candidate_protocol_freeze"

        protocol = {
            "milestone": MILESTONE,
            "protocol_id": PROTOCOL_ID,
            "candidate_count": 1,
            "candidate_name": (
                "bounded physical-occupancy split-state grid-to-streamline "
                "parent projection"
            ),
            "authoritative_global_parent_state": (
                "A2-E exact Cartesian parent_component_mass_kg"
            ),
            "geometry": {
                "subsegment_authority": "frozen SG7D operator",
                "physical_cell_pore_volume": "A2-E pore_volume_m3",
                "W_c": "sum_{q:c(q)=c} PV_q",
                "CV_index": "r = streamline*200 + control_volume",
            },
            "bounded_projection": {
                "denominator": "D_c = max(PV_cell_c, W_c)",
                "subsegment_mass": (
                    "m_q = M_parent[c(q)] * PV_q / D_c"
                ),
                "cell_to_streamline_mass": (
                    "M_SL,c = M_parent,c * W_c / max(PV_cell_c, W_c)"
                ),
                "streamline_occupancy_fraction": (
                    "alpha_c = min(1, W_c / PV_cell_c)"
                ),
                "equivalent_cell_mapping": (
                    "M_SL,c = alpha_c * M_parent,c"
                ),
                "CV_mass": (
                    "M_CV,r = sum_{q:r(q)=r} m_q"
                ),
            },
            "residual_grid_state": {
                "cell_residual": (
                    "R_c = M_parent,c - M_SL,c"
                ),
                "equivalent": (
                    "R_c = M_parent,c * max(0, 1 - W_c/PV_cell_c)"
                ),
                "outside_S0": (
                    "W_c = 0 therefore R_c = M_parent,c exactly"
                ),
                "inside_undercovered_S0": (
                    "physically unrepresented parent mass remains in the same Cartesian cell"
                ),
                "inside_unit_or_overcovered_S0": (
                    "R_c = 0; full cell mass is represented without duplication"
                ),
                "reverse_halo_pullback": False,
            },
            "guaranteed_algebraic_properties": [
                "m_q >= 0 for nonnegative parent mass",
                "0 <= M_SL,c <= M_parent,c for every Cartesian cell",
                "R_c >= 0 for every Cartesian cell",
                "sum_r M_CV,r + sum_c R_c = sum_c M_parent,c up to numerical roundoff",
                "no cell contributes more than its exact authoritative parent mass",
                "over-covered cells cannot duplicate parent mass because D_c=W_c",
                "under-covered cells cannot concentrate whole-cell mass into partial tube occupancy because D_c=PV_cell_c",
            ],
            "capacity_monotonicity_relative_to_F2R1_diagnostic": {
                "diagnostic_edge_mass": (
                    "m_q_diag = M_parent[c(q)] * PV_q / PV_cell_c"
                ),
                "bounded_edge_mass_relation": (
                    "m_q <= m_q_diag because max(PV_cell_c,W_c) >= PV_cell_c"
                ),
                "CV_mass_relation": (
                    "M_CV,r <= M_CV,r_diag elementwise for every CV"
                ),
                "F2R1_diagnostic_overloaded_CV_count": 0,
                "prospective_implication": (
                    "the frozen bounded candidate is prospectively capacity-feasible "
                    "for the same Day365 geometry/capacity state, but execution must "
                    "still certify this in F2-R3"
                ),
            },
            "scientific_interpretation": {
                "streamline_CV_state": (
                    "only the parent component mass occupying pore volume represented "
                    "by the refreshed streamline tubes"
                ),
                "residual_grid_state": (
                    "the complementary parent mass not represented by those tubes; "
                    "this includes residual mass inside under-covered S0 cells"
                ),
                "global_recurrent_authority_remains_grid": True,
                "streamline_state_is_derived_transport_coordinate_state": True,
            },
            "why_no_LP_in_R2": (
                "F2-R1 already showed the non-renormalized physical-PV diagnostic "
                "has zero overloaded CVs. The bounded denominator above is elementwise "
                "no larger in assigned mass than that diagnostic and also prevents "
                "mass duplication in W_c>PV_cell cells. Therefore a redistribution LP "
                "would add unneeded mass movement before this simpler local operator "
                "is tested."
            ),
            "prohibitions": [
                "no clipping or mass discard",
                "no global saturation rescaling",
                "no relaxation of S_max=0.80",
                "no increase of E37A CV capacity",
                "no halo/support expansion",
                "no reverse H1->S0 transfer",
                "no transport along Cartesian support graph",
                "no LP/min-cost flow execution in F2-R2",
                "no fitting to future target state or acceptance truth",
                "no teacher/model execution",
            ],
        }

        execution_gates = {
            "milestone": "POSTV16-AV4-F2-R3",
            "name": (
                "Controlled Bounded Physical-Occupancy Parent-State Projection Execution"
            ),
            "authorized": True,
            "single_candidate_only": True,
            "required_operator": (
                "m_q = M_parent[c(q)] * PV_q / max(PV_cell_c, W_c)"
            ),
            "required_gates": [
                "exact reproduction of F2-R1 Day365 authorities",
                "cellwise 0 <= mapped_mass <= exact_parent_mass",
                "cellwise residual >= 0",
                "exact global mapped-plus-residual component-mass ledger",
                "zero CV capacity excess within frozen numerical tolerance",
                "E37A CV mass-to-saturation inversion PASS",
                "CV saturation finite and within [0.20,0.80]",
                "no support/domain modification",
                "no halo reverse pullback",
                "no model/teacher/time advance",
            ],
            "scientific_outcomes": {
                "F2R3_PASS_SPLIT_STATE": (
                    "all conservation/capacity/inversion gates pass; accepted restart "
                    "state is CV component mass plus exact Cartesian residual mass"
                ),
                "F2R3_SCIENTIFIC_FAIL": (
                    "the single frozen bounded candidate violates physical capacity "
                    "or another frozen scientific feasibility gate"
                ),
                "F2R3_TECHNICAL_BLOCK": (
                    "authority/schema/module/numerical implementation failure before "
                    "a valid scientific decision"
                ),
            },
            "repair_search_authorized": False,
            "alternate_candidate_authorized": False,
            "F3_authorized_now": False,
            "A3_E2_authorized": False,
            "AV4_dynamic_transport_execution_authorized": False,
        }

        restart_architecture = {
            "milestone": MILESTONE,
            "authoritative_global_state": {
                "component_mass_grid": list(GRID),
                "role": "global recurrent physical authority",
            },
            "derived_transport_state": {
                "component_mass_CV": [NSL, NCV],
                "saturation_CV": [NSL, NCV],
                "role": "refreshed streamline-coordinate transport state",
            },
            "residual_state": {
                "component_mass_grid_residual": list(GRID),
                "role": (
                    "exact complement of parent grid mass not represented in "
                    "refreshed streamline tube occupancy"
                ),
                "may_exist_inside_S0": True,
            },
            "future_F3_question_if_F2R3_passes": (
                "freeze how the residual grid state participates in a 365->500 "
                "restart transport interval without violating global conservation "
                "or inventing reverse streamline coverage"
            ),
            "neural_input_dimension_frozen": False,
        }

        decision = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "F2_scientific_FAIL_preserved": True,
            "F2R1_localization_bound": True,
            "repair_candidate_count": 1,
            "bounded_physical_occupancy_candidate_frozen": True,
            "repair_execution_performed": False,
            "LP_execution_performed": False,
            "support_domain_changed": False,
            "mass_clipped_or_discarded": False,
            "global_rescaling_performed": False,
            "saturation_bound_changed": False,
            "teacher_transport_performed": False,
            "checkpoint_inference_performed": False,
            "physical_time_advanced": False,
            "F2R3_authorized": True,
            "F2R3_execution_authorized": True,
            "F3_authorized": False,
            "A3_E2_authorized": False,
            "AV4_dynamic_transport_execution_authorized": False,
        }

        summary = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "protocol_id": PROTOCOL_ID,
            "F2R1_overloaded_CV_count": 32919,
            "F2R1_global_CV_capacity_sufficient": True,
            "F2R1_physicalPV_diagnostic_overloaded_CV_count": 0,
            "frozen_operator": (
                "m_q = M_parent[c(q)] * PV_q / max(PV_cell_c, W_c)"
            ),
            "residual_inside_undercovered_S0_allowed": True,
            "repair_execution": False,
            "candidate_count": 1,
            "F2R3_authorized": True,
            "F3_authorized": False,
            "A3_E2_authorized": False,
            "AV4_dynamic_transport_execution_authorized": False,
        }

        files = {
            "PAD_Stream_POSTV16_AV4_F2_R2_Summary.json":
                json_bytes(summary),
            "POSTV16_AV4_F2_R2_Bounded_Physical_Occupancy_Projection_Protocol.json":
                json_bytes(protocol),
            "POSTV16_AV4_F2_R2_Restart_State_Architecture_Contract.json":
                json_bytes(restart_architecture),
            "POSTV16_AV4_F2_R2_F2R3_Execution_Handoff_Contract.json":
                json_bytes(execution_gates),
            "POSTV16_AV4_F2_R2_Decision_Contract.json":
                json_bytes(decision),
            "POSTV16_AV4_F2_R2_Final_Gate_Matrix.csv":
                csv_bytes([{"gate": k, **v} for k, v in gates.items()]),
        }

        immutable_publish(out, files)

        manifest_rows = []
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name != "POSTV16_AV4_F2_R2_Artifact_Manifest.csv":
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
                "POSTV16_AV4_F2_R2_Artifact_Manifest.csv":
                    csv_bytes(manifest_rows)
            },
        )

        print()
        print("=" * 214)
        print(f"{MILESTONE}: BOUNDED PHYSICAL-OCCUPANCY PROJECTION PROTOCOL FREEZE PASS")
        print("=" * 214)
        print("F2 scientific FAIL                         : PRESERVED")
        print("F2-R1 localization                        : BOUND")
        print("Frozen candidate count                    : 1")
        print("Frozen denominator                        : max(PV_cell, W_c)")
        print("Residual inside under-covered S0          : ALLOWED / REQUIRED BY LEDGER")
        print("Physical-PV diagnostic overload count     : 0 (evidence only)")
        print("Repair execution                          : False")
        print("LP / support expansion                    : False / False")
        print("POSTV16-AV4-F2-R3                         : AUTHORIZED")
        print("F2-R3 execution                           : AUTHORIZED")
        print("F3 / A3-E2 / dynamic transport            : NOT AUTHORIZED")
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
            "F2_scientific_FAIL_preserved": True,
            "repair_execution_performed": False,
            "LP_execution_performed": False,
            "support_domain_changed": False,
            "mass_clipped_or_discarded": False,
            "physical_time_advanced": False,
            "F2R3_authorized": False,
            "F3_authorized": False,
            "A3_E2_authorized": False,
            "AV4_dynamic_transport_execution_authorized": False,
            "automatic_rerun_authorized": False,
        }
        data = json_bytes(report)
        p = blocked / "POSTV16_AV4_F2_R2_Blocked_Report.json"
        if p.exists() and p.read_bytes() != data:
            p = blocked / (
                "POSTV16_AV4_F2_R2_Blocked_Report_"
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
        print("F2 scientific FAIL remains immutable.")
        print("NO REPAIR EXECUTION OR ALTERNATE CANDIDATE AUTHORIZED.")
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
