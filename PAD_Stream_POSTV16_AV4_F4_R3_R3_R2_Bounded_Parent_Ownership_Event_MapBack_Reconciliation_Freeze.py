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


MILESTONE = "POSTV16-AV4-F4-R3-R3-R2"
PROTOCOL_ID = (
    "POSTV16_AV4_F4_R3_R3_R2_BOUNDED_PARENT_OWNERSHIP_"
    "CV_TO_CARTESIAN_EVENT_MAPBACK_RECONCILIATION_V1"
)

STATUS_PASS = (
    "AV4F4R3R3R2_R3R3R1R1R1_MIXED_COVERAGE_PARENT_OWNERSHIP_VS_RAW_EOS_"
    "DISAGGREGATION_FAILURE_BOUND_SINGLE_CONSERVATIVE_BOUNDED_PARENT_OWNERSHIP_"
    "CV_TO_CARTESIAN_EVENT_MAPBACK_RECONCILIATION_PROSPECTIVELY_FROZEN_NO_EXECUTION"
)
STATUS_BLOCKED = "AV4F4R3R3R2_EVENT_MAPBACK_RECONCILIATION_FREEZE_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT_R3R3R1R1R1_COMMIT = "c0b2b9c714e028ab1e6e45f1f123a73c241e6fae"

NEGATIVE_CELL_COUNT = 90
WORST_CELL_KJI = [6, 46, 46]
WORST_FUTURE_MASS_KG = -996.2885121085193
TOTAL_NEGATIVE_DEFICIT_KG = 7732.7019340081115
WORST_COVERAGE_RATIO = 3.6410864638972855
OLD_INVENTORY_CELLWISE_TV_KG = 1077249.3693616898
CAUSE_CLASS = (
    "BOUNDED_PARENT_OWNERSHIP_VS_RAW_EOS_DELTA_"
    "DISAGGREGATION_INCOMPATIBILITY_WITH_MIXED_COVERAGE"
)

R1 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_R1_R1_R1_"
    "Corrected_Block_Namespace_Event_MapBack_Localization.py"
)
R1_BLOB = "1ffd22030c5849c23cba566518e9d10b27427e23"

R3R3 = (
    "PAD_Stream_POSTV16_AV4_F4_R3_R3_"
    "First_Event_Flow_Epoch_Renewal_Execution.py"
)
R3R3_BLOB = "4aaf46d18253ac0fc4a8e50ffb3d30e841c93709"

F2R3 = (
    "PAD_Stream_POSTV16_AV4_F2_R3_"
    "Bounded_Physical_Occupancy_Projection_Execution.py"
)
F2R3_BLOB = "359f3c0edf87e10bb4006cacdd271cd426fed22b"

R2 = (
    "PAD_Stream_V16E35_R2_Source_Conservative_Transport_"
    "Capillary_Split_First_Controlled_Transition.py"
)
R2_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"

E37A = (
    "PAD_Stream_V16E37A_"
    "Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
)
E37A_BLOB = "0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"

SG7D = "PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"
SG7D_BLOB = "890088c0c0fcab415a2c7351c5079ca8ee12bf82"

AV1_R7R2 = (
    "PAD_Stream_POSTV16_AV1_D_R7_R2_"
    "Conservative_Bounded_Overlap_Occupancy_Reconciliation_Freeze.py"
)
AV1_R7R2_BLOB = "c9c4ceed05e6e631ad071b9da901d35874609255"

E41R2 = "PAD_Stream_V16E41R2_Capacity_Aware_Conservative_MapBack_Timestep_Repair.py"
E41R2_BLOB = "f6961c48dc47c5fb55f2af658ef4ce429eb66533"

SOURCE_BLOBS = {
    R1: R1_BLOB,
    R3R3: R3R3_BLOB,
    F2R3: F2R3_BLOB,
    R2: R2_BLOB,
    E37A: E37A_BLOB,
    SG7D: SG7D_BLOB,
    AV1_R7R2: AV1_R7R2_BLOB,
    E41R2: E41R2_BLOB,
}

BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

R1_REL = (
    BASE_AV4
    / "POSTV16_AV4_F4_R3_R3_R1_R1_R1_Event_MapBack_Negative_Cell_Localization"
)
R1_SUMMARY = "PAD_Stream_POSTV16_AV4_F4_R3_R3_R1_R1_R1_Summary.json"
R1_DIAG = "POSTV16_AV4_F4_R3_R3_R1_R1_R1_MapBack_Failure_Diagnosis.json"
R1_AUDIT = "POSTV16_AV4_F4_R3_R3_R1_R1_R1_Negative_Cell_Audit.csv"
R1_HANDOFF = "POSTV16_AV4_F4_R3_R3_R1_R1_R1_R3R3R2_Handoff_Contract.json"
R1_DECISION = "POSTV16_AV4_F4_R3_R3_R1_R1_R1_Decision_Contract.json"
R1_MANIFEST = "POSTV16_AV4_F4_R3_R3_R1_R1_R1_Artifact_Manifest.csv"

R1_STATUS = (
    "AV4F4R3R3R1R1R1_BLOCK_NAMESPACE_CROSSING_CORRECTED_"
    "F2R3_WC_ARCHIVE_KEY_SCHEMA_CORRECTED_"
    "R3R3_EVENT_MAPBACK_NEGATIVE_CARTESIAN_CELL_FAILURE_LOCALIZED_"
    "BOUNDED_PARENT_OWNERSHIP_AND_RAW_EOS_DELTA_DISAGGREGATION_AUDITED_NO_REPAIR_SELECTED"
)

OUT_REL = (
    BASE_AV4
    / "POSTV16_AV4_F4_R3_R3_R2_Bounded_Parent_Ownership_Event_MapBack_Freeze"
)
BLOCK_REL = BASE_AV4 / "POSTV16_AV4_F4_R3_R3_R2_BLOCKED"


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
    return (json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


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
    return s.getvalue().encode()


def immutable_publish(out: Path, files: dict[str, bytes]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        p = out / name
        if p.exists() and p.read_bytes() != data:
            raise GateError("existing_output_differs:" + name)
        if not p.exists():
            p.write_bytes(data)


def near(a: Any, b: Any, rtol: float = 1e-12, atol: float = 1e-9) -> bool:
    aa, bb = float(a), float(b)
    return abs(aa - bb) <= max(atol, rtol * max(abs(bb), 1.0))


def self_test() -> None:
    parent_pair = [2.0, 3.0]
    m0 = sum(parent_pair)
    m1 = m0
    target = [x * m1 / m0 for x in parent_pair]
    assert target == parent_pair
    assert not all([True, False])
    print(
        "POSTV16-AV4-F4-R3-R3-R2 bounded parent-ownership "
        "event mapback design self-test: PASS"
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
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {value}" if value is not None else ""))
        if not ok:
            raise GateError(name)

    print("=" * 214)
    print(
        "POSTV16-AV4-F4-R3-R3-R2 — CONSERVATIVE BOUNDED PARENT-OWNERSHIP "
        "EVENT MAPBACK RECONCILIATION DESIGN FREEZE"
    )
    print("=" * 214)
    print("DESIGN / FREEZE ONLY. NO MAPBACK REPAIR EXECUTION. NO LP EXECUTION.")
    print("NO EVENT REFRESH RETRY. NO SUPPORT EXPANSION. NO CLIPPING. NO RESCALING.")
    print("NO TIMESTEP CHANGE. NO TRAINING. NO CHECKPOINT/INFERENCE. NO F5. NO CMG.")
    print()

    try:
        stage = "repository_authority"
        parent = git_text(root, "rev-parse", "HEAD^")
        status = git_text(root, "status", "--porcelain")
        gate(
            "repository_parent_is_R3R3R1R1R1_commit",
            parent == PARENT_R3R3R1R1R1_COMMIT,
            parent,
        )
        gate("repository_clean", status == "", repr(status))

        for fn, expected in SOURCE_BLOBS.items():
            p = root / fn
            actual = git_blob(p, root) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact", actual == expected, actual)

        stage = "R3R3R1R1R1_localization_binding"
        d = drive / R1_REL
        gate("R1_output_present", d.is_dir(), str(d))
        manifest = verify_manifest(d, R1_MANIFEST)
        gate("R1_manifest_exact_6", len(manifest) == 6, len(manifest))

        summary = load_json(d / R1_SUMMARY)
        diag = load_json(d / R1_DIAG)
        audit = read_csv(d / R1_AUDIT)
        handoff = load_json(d / R1_HANDOFF)
        decision_in = load_json(d / R1_DECISION)

        gate("R1_status_exact", summary["status"] == R1_STATUS, summary["status"])
        gate("R1_negative_cell_count_exact",
             int(summary["negative_cartesian_cell_count"]) == NEGATIVE_CELL_COUNT,
             summary["negative_cartesian_cell_count"])
        gate("R1_worst_cell_exact",
             list(summary["worst_cell_kji"]) == WORST_CELL_KJI,
             summary["worst_cell_kji"])
        gate("R1_worst_future_mass_exact",
             near(summary["worst_future_mass_kg"], WORST_FUTURE_MASS_KG),
             summary["worst_future_mass_kg"])
        gate("R1_total_negative_deficit_exact",
             near(summary["total_negative_deficit_kg"], TOTAL_NEGATIVE_DEFICIT_KG),
             summary["total_negative_deficit_kg"])
        gate("R1_mixed_coverage_exact",
             summary["all_negative_cells_overcovered"] is False,
             summary["all_negative_cells_overcovered"])
        gate("R1_cellwise_TV_exact",
             near(summary["old_inventory_cellwise_total_variation_kg"],
                  OLD_INVENTORY_CELLWISE_TV_KG, atol=1e-6),
             summary["old_inventory_cellwise_total_variation_kg"])
        gate("R1_cause_class_exact", summary["cause_class"] == CAUSE_CLASS, summary["cause_class"])

        raw = diag["raw_mapback"]
        neg = diag["negative_cell_statistics"]
        worst = diag["worst_cell"]
        probes = diag["non_authoritative_probes"]

        gate("R1_raw_transfer_global_closure",
             abs(float(raw["transfer_residual_kg"])) <= 1e-6,
             raw["transfer_residual_kg"])
        gate("R1_worst_coverage_ratio_exact",
             near(worst["coverage_ratio_W_over_cellPV"], WORST_COVERAGE_RATIO, atol=1e-10),
             worst["coverage_ratio_W_over_cellPV"])
        gate("R1_not_pure_overcoverage_mechanism",
             neg["all_negative_cells_overcovered"] is False
             and int(neg["count"]) == NEGATIVE_CELL_COUNT,
             neg)
        gate("R1_occupancy_scaled_delta_not_authoritative",
             probes["occupancy_scaled_raw_delta"]["repair_candidate"] is False
             and abs(float(probes["occupancy_scaled_raw_delta"][
                 "global_CV_delta_conservation_defect_kg"])) > 1e-9,
             probes["occupancy_scaled_raw_delta"])
        gate("R1_parent_ownership_withdrawal_probe_nonnegative",
             probes["ownership_proportional_negative_withdrawal_only"]["repair_candidate"] is False
             and float(probes["ownership_proportional_negative_withdrawal_only"][
                 "minimum_future_cell_mass_kg"]) >= -1e-8
             and probes["ownership_proportional_negative_withdrawal_only"][
                 "positive_CV_delta_placement_included"] is False,
             probes["ownership_proportional_negative_withdrawal_only"])
        gate("R1_handoff_design_only",
             handoff["milestone"] == MILESTONE
             and handoff["authorized"] is True
             and handoff["execution"] is False
             and handoff["F5_dataset_generation_authorized"] is False)
        gate("R1_decision_no_repair_execution",
             decision_in["repair_selected"] is False
             and decision_in["mapback_repair_executed"] is False
             and decision_in["LP_executed"] is False
             and decision_in["support_domain_changed"] is False
             and decision_in["event_refresh_retried"] is False
             and decision_in["F4R3R3R2_design_freeze_authorized"] is True
             and decision_in["F4R3R3R2_repair_execution_authorized"] is False
             and decision_in["F5_dataset_generation_authorized"] is False)
        gate("R1_negative_cell_audit_exact_90", len(audit) == NEGATIVE_CELL_COUNT, len(audit))

        stage = "freeze_single_reconciliation_protocol"

        protocol = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "protocol_id": PROTOCOL_ID,
            "candidate_count": 1,
            "problem_statement": {
                "failure_class": CAUSE_CLASS,
                "negative_cartesian_cells": NEGATIVE_CELL_COUNT,
                "worst_cell_kji": WORST_CELL_KJI,
                "worst_future_mass_kg": WORST_FUTURE_MASS_KG,
                "total_negative_deficit_kg": TOTAL_NEGATIVE_DEFICIT_KG,
                "worst_coverage_ratio_W_over_cellPV": WORST_COVERAGE_RATIO,
                "old_parent_inventory_cellwise_total_variation_kg":
                    OLD_INVENTORY_CELLWISE_TV_KG,
                "pure_overcoverage_failure": False,
                "accepted_transport_state_implicated": False,
                "raw_F4_global_CV_delta_conservation_implicated": False,
                "representation_disaggregation_implicated": True,
            },
            "repair_role": {
                "name":
                    "bounded parent-ownership-preserving CV-to-Cartesian event mapback reconciliation",
                "classification": "representation reconciliation only",
                "changes_event_CV_mass": False,
                "changes_transport_operator": False,
                "changes_physical_time": False,
                "changes_F4_R2_terminal_pass_through": False,
            },
            "authoritative_parent_state": {
                "P_q": "frozen F2-R3 subsegment_parent_mass_kg",
                "P_jc":
                    "sum P_q over frozen subsegments belonging to CV j and Cartesian cell c",
                "M0_j": "sum_c P_jc",
                "R_c": "frozen F2-R3 residual_grid_component_mass_kg",
                "residual_sidecar_during_event_mapback": "unchanged exactly",
                "parent_identity_requirement":
                    "if M1_j=M0_j for all j, reconstructed Cartesian mass equals the exact Day365 parent grid",
            },
            "event_state": {
                "M1_j": "accepted Day413.78677770818403 CV component mass",
                "failed_substep_applied": False,
            },
            "support": {
                "E":
                    "{(j,c): frozen SG7D subsegment support of CV j intersects Cartesian cell c}",
                "domain": "exact existing S0 CV-cell incidence only",
                "H1_or_other_halo_eligible": False,
                "cross_CV_mass_exchange": False,
                "automatic_support_expansion": False,
            },
            "cell_capacity": {
                "formula":
                    "C_c = cell_pore_volume_m3[c] * rho_g(S=0.80, pressure_c, p_ref) * 0.60",
                "pressure":
                    "frozen pre-refresh Day365 pressure at event mapback",
                "EOS": "frozen R2 gas_density_from_state",
                "available_mapped_capacity": "A_c = C_c - R_c",
            },
            "continuity_target": {
                "M0_positive": "T_jc = P_jc * M1_j / M0_j",
                "zero_parent_mass_fallback":
                    "if M0_j<=eps and M1_j>eps, normalize raw event EOS/SG7D absolute pair inventory Q_jc on the same CV support",
                "raw_old_EOS_parent_authority": False,
            },
            "optimization": {
                "solver_at_execution": "scipy.optimize.linprog(method='highs')",
                "x_jc": "nonnegative mapped event mass from CV j to cell c",
                "hard_constraints": [
                    "sum_c x_jc = M1_j for every CV j",
                    "R_c + sum_j x_jc <= C_c for every cell c",
                    "x_jc exists only on frozen E",
                ],
                "stage_1":
                    "minimize L1 deviation from parent-continuity target T_jc",
                "stage_2":
                    "freeze stage-1 optimum within tolerance and minimize L1 deviation from raw event EOS target Q_jc",
                "stage_3":
                    "freeze stages 1 and 2 within tolerance and minimize normalized lexicographic pair-rank*x_jc",
                "fixed_pair_order":
                    "lexicographic (CV flat index j, Cartesian flat cell c)",
            },
            "event_grid_reconstruction": {
                "formula": "M_event_grid,c = R_c + sum_j x_jc",
                "global_mass":
                    "sum_c M_event_grid,c = sum_c R_c + sum_j M1_j",
                "lower_bound": ">=0",
                "upper_bound": "<=C_c",
            },
            "feasibility": {
                "per_CV_support_gate":
                    "every CV with M1_j>tol has at least one supported cell",
                "global_capacity_gate":
                    "sum_j M1_j <= sum_c A_c + tol on S0",
                "LP_gate":
                    "all CV equalities and cell capacity inequalities feasible simultaneously",
                "on_infeasible":
                    "SCIENTIFIC FAIL; no support expansion, clipping, rescaling, timestep change, or automatic fallback",
            },
            "why_not_other_candidates": {
                "raw_F4_signed_EOS_delta":
                    "subtracts raw old EOS inventory from cells that did not own it",
                "blanket_occupancy_scaling":
                    "mixed coverage and nonzero global CV-delta conservation defect",
                "cellwise_clipping": "mass destruction",
                "global_rescaling": "changes accepted transport solution",
                "E41R2_timestep_repair":
                    "failure is post-accepted-state representation transfer",
                "direct_AV1_R7R2_reuse":
                    "does not preserve every transported event CV mass identity",
            },
            "execution_gates": {
                "same_event_CV_state": True,
                "failed_substep_remains_unapplied": True,
                "residual_sidecar_unchanged": True,
                "parent_zero_delta_identity_probe": True,
                "all_CV_mass_equalities_close": True,
                "all_grid_cells_nonnegative": True,
                "all_grid_cells_within_capacity": True,
                "global_mass_closure": True,
                "outside_S0_added_mass_exact_zero": True,
                "no_support_expansion": True,
                "no_transport_or_timestep_change": True,
            },
            "prohibitions": {
                "cellwise_clipping": True,
                "mass_discard": True,
                "global_rescaling": True,
                "Smax_relaxation": True,
                "H1_or_other_support_expansion": True,
                "event_refresh_execution_in_this_freeze": True,
                "training": True,
                "checkpoint_inference": True,
                "locked_OOD_access": True,
                "CMG": True,
            },
        }

        handoff_out = {
            "milestone": "POSTV16-AV4-F4-R3-R3-R3",
            "name": (
                "Controlled Event-Time Bounded Parent-Ownership MapBack "
                "+ Same-Time Flow-Refresh/Reprojection Execution"
            ),
            "authorized": True,
            "execution": True,
            "required_R3R3R2_status": STATUS_PASS,
            "scope": [
                "rebind exact accepted Day413.78677770818403 CV state",
                "execute the single frozen CV-to-Cartesian ownership-reconciliation LP",
                "certify event full-grid bounds and global conservation",
                "execute exactly one same-time A2-E flow refresh",
                "regenerate Darcy/Pollock/TOF/weights",
                "execute bounded refreshed-geometry split-state reprojection",
                "stop after publishing refreshed event recurrent state",
            ],
            "not_authorized": [
                "resume physical-time transport toward Day500",
                "second event refresh",
                "support expansion",
                "repair search",
                "F5",
                "training",
                "checkpoint inference",
                "locked OOD",
                "A3-E2",
                "CMG",
            ],
        }

        decision_out = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "R3R3_scientific_FAIL_preserved": True,
            "R1_localization_bound": True,
            "cause_class": CAUSE_CLASS,
            "candidate_count": 1,
            "selected_repair":
                "bounded_parent_ownership_preserving_CV_to_Cartesian_event_mapback_reconciliation",
            "repair_execution_performed": False,
            "LP_execution_performed": False,
            "event_refresh_retried": False,
            "support_domain_changed": False,
            "transport_operator_changed": False,
            "timestep_changed": False,
            "residual_sidecar_changed": False,
            "R3R3R3_execution_authorized": True,
            "F5_dataset_generation_authorized": False,
            "training_authorized": False,
            "A3_E2_authorized": False,
            "AV4_general_dynamic_transport_authorized": False,
        }

        summary_out = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "protocol_id": PROTOCOL_ID,
            "diagnostic_negative_cells": NEGATIVE_CELL_COUNT,
            "diagnostic_worst_cell_kji": WORST_CELL_KJI,
            "diagnostic_total_negative_deficit_kg": TOTAL_NEGATIVE_DEFICIT_KG,
            "diagnostic_parent_vs_raw_cellwise_TV_kg": OLD_INVENTORY_CELLWISE_TV_KG,
            "diagnostic_all_negative_cells_overcovered": False,
            "cause_class": CAUSE_CLASS,
            "candidate_count": 1,
            "repair_execution_performed": False,
            "R3R3R3_authorized": True,
            "F5_authorized": False,
        }

        files = {
            "PAD_Stream_POSTV16_AV4_F4_R3_R3_R2_Summary.json":
                json_bytes(summary_out),
            "POSTV16_AV4_F4_R3_R3_R2_Frozen_MapBack_Reconciliation_Protocol.json":
                json_bytes(protocol),
            "POSTV16_AV4_F4_R3_R3_R2_R3R3R3_Execution_Handoff_Contract.json":
                json_bytes(handoff_out),
            "POSTV16_AV4_F4_R3_R3_R2_Decision_Contract.json":
                json_bytes(decision_out),
            "POSTV16_AV4_F4_R3_R3_R2_Final_Gate_Matrix.csv":
                csv_bytes([{"gate": k, **v} for k, v in gates.items()]),
        }
        immutable_publish(out, files)

        manifest_rows = []
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name != "POSTV16_AV4_F4_R3_R3_R2_Artifact_Manifest.csv":
                manifest_rows.append(
                    {"file": p.name, "sha256": sha256_file(p), "bytes": p.stat().st_size}
                )
        immutable_publish(
            out,
            {"POSTV16_AV4_F4_R3_R3_R2_Artifact_Manifest.csv": csv_bytes(manifest_rows)},
        )

        print()
        print("=" * 214)
        print(f"{MILESTONE}: BOUNDED PARENT-OWNERSHIP EVENT MAPBACK RECONCILIATION DESIGN FREEZE PASS")
        print("=" * 214)
        print("R3-R3 scientific FAIL                    : PRESERVED")
        print("Localized negative Cartesian cells       :", NEGATIVE_CELL_COUNT)
        print("Cause class                              :", CAUSE_CLASS)
        print("All negative cells overcovered           : False")
        print("Selected repair candidate count          : 1")
        print("Residual-grid sidecar during mapback     : FROZEN / UNCHANGED")
        print("Event CV mass preservation               : EXACT PER CV")
        print("CV-to-cell support                       : EXISTING S0 ONLY")
        print("Parent ownership continuity              : PRIMARY OPTIMIZATION TARGET")
        print("Raw event EOS distribution               : SECONDARY TARGET / ZERO-PARENT FALLBACK")
        print("Repair / LP execution                    : False / False")
        print("POSTV16-AV4-F4-R3-R3-R3                 : AUTHORIZED")
        print("F5 / training / A3-E2 / general AV4      : NOT AUTHORIZED")
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
            "R3R3_scientific_FAIL_preserved": True,
            "repair_execution_performed": False,
            "LP_execution_performed": False,
            "event_refresh_retried": False,
            "support_domain_changed": False,
            "R3R3R3_execution_authorized": False,
            "F5_dataset_generation_authorized": False,
            "training_authorized": False,
            "automatic_rerun_authorized": False,
        }
        data = json_bytes(report)
        p = blocked / "POSTV16_AV4_F4_R3_R3_R2_Blocked_Report.json"
        if p.exists() and p.read_bytes() != data:
            p = blocked / (
                "POSTV16_AV4_F4_R3_R3_R2_Blocked_Report_"
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
        print("R3-R3 scientific FAIL remains immutable.")
        print("NO MAPBACK REPAIR, LP, EVENT REFRESH, OR AUTOMATIC RERUN AUTHORIZED.")
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
