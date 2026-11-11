#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import numpy as np

M = "POSTV16-AV4-PIVOT-GPU-HYB-G0"
NAME = "Cadence-Aware Hybrid BL-DP / Current AV4 Pivot Integration Contract Freeze"
PASS = "POSTV16AV4PIVOTGPUHYBG0_CADENCE_AWARE_HYBRID_BLDP_INTEGRATION_CONTRACT_FREEZE_PASS_NO_PHYSICS_EXECUTION"
BLOCK = "POSTV16AV4PIVOTGPUHYBG0_TECHNICAL_OR_AUTHORITY_BLOCK_NO_PHYSICS_EXECUTION"

BRANCH = "postv16-av4-pivot"
PARENT = "bb68634ca0f7b28ed1a69028bf0cd01bba8e7036"  # P-CAD-A2

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

# --------------------------------------------------------------------------------------
# Current cadence authority.
# --------------------------------------------------------------------------------------
PCAD_A2_RUNNER = "PAD_Stream_POSTV16_P_CAD_A2_HoldEnvelope_FailureDriver_and_GPU_TargetedProbe_Protocol_Freeze.py"
PCAD_A2_BLOB = "6387abe0754c6a1e8e0fd2fb935283766af2a5e7"
PCAD_A2_REL = BASE_AV4 / "POSTV16_P_CAD_A2_HoldEnvelope_FailureDriver_and_GPU_TargetedProbe_Protocol_Freeze"
PCAD_A2_SUMMARY = "PAD_Stream_POSTV16_P_CAD_A2_Summary.json"
PCAD_A2_DECISION = "POSTV16_P_CAD_A2_Decision_Contract.json"
PCAD_A2_GPU_PROTOCOL = "POSTV16_P_CAD_A2_GPU_Targeted_Probe_Protocol.csv"
PCAD_A2_MANIFEST = "POSTV16_P_CAD_A2_Artifact_Manifest.csv"
PCAD_A2_STATUS = "POSTV16PCADA2_HOLD_ENVELOPE_FAILURE_DRIVER_AND_GPU_TARGETED_PROBE_PROTOCOL_FREEZE_PASS_NO_PHYSICS_EXECUTION"

# --------------------------------------------------------------------------------------
# Existing Hybrid BL-DP / SGSim deployment authority.
# --------------------------------------------------------------------------------------
E11_RUNNER = "PAD_Stream_V16E11_R2_Packed_SG5_Serialization_Repair_and_Controlled_Hybrid_Streamline_Pilot.py"
E11_RUNNER_BLOB = "bf89c14a3cb177fb483e233a17b72e824d31119b"
E11_REL = Path("pilots/hybrid_dp/V16E11_R2_SGSIM_100D_CONTROLLED_STREAMLINE_PILOT")
E11_PILOT = ("V16E11_R2_SGSim_100Day_Streamline_Pilot.npz", "710720e933d740787868a9894fa04f90e88429c120d9f86a52b750f4c41db844")
E11_AUDIT = ("V16E11_R2_Path_Eligibility_and_Screening_Audit.json", "170dde9c74b26f949ef90de3d67001a124e740822fe587c032ae2f066379df4f")
E11_SUMMARY = ("PAD_Stream_V16E11_R2_Summary.json", "76336276daf4a506ea7e0880a6ad2e2852724deaf4623ca3945eafbf029e4243")
E11_HANDOFF = ("V16E11_R2_Handoff.md", "d0eb4f3da3741ea5db96420652f6f9ebd76a1684d3efa400fa4a2db3d8f4aa11")

E12_RUNNER = "PAD_Stream_V16E12_R1_Route_Semantics_Reconciliation_and_Conservative_MapBack_Protocol_Freeze.py"
E12_RUNNER_BLOB = "ed419ecd2cd23421625b655461a74bb4d9d35fb3"
E12_REL = Path("provenance/hybrid_dp/V16E12_R1_ROUTE_SEMANTICS_RECONCILED_PILOT_EVIDENCE_AND_MAPBACK_PROTOCOL_FREEZE")
E12_SUMMARY = "PAD_Stream_V16E12_R1_Summary.json"
E12_PROTOCOL = "V16E12_R1_Conservative_MapBack_Protocol.json"
E12_RESULTS = "V16E12_R1_Protocol_Freeze_Results.json"

E9_ADAPTER = "PAD_Stream_V16E9_Hybrid_Transport_Adapter.py"
E9_ADAPTER_BLOB = "83e3340424f43ceda604c403e955435036cf6661"

EXPECTED_STREAMLINES = 1078
EXPECTED_NXI = 201
EXPECTED_ROUTE_COUNTS = {
    "HYBRID10_ACCEPT": 462,
    "HYBRID12_ACCEPT": 0,
    "EXACT_R2_FALLBACK": 41,
    "FULL_PHYSICS_SG7A_FALLBACK": 575,
}
EXPECTED_EARLY_PROBES = [[75, 80], [120, 125], [40, 45]]

OUT_TOKEN = "POSTV16_AV4_PIVOT_GPU_HYB_G0"
OUT_REL = BASE_AV4 / (OUT_TOKEN + "_Cadence_Aware_Hybrid_BLDP_Integration_Contract_Freeze")
STAGE_REL = BASE_AV4 / (OUT_TOKEN + "_STAGING")
BLOCK_REL = BASE_AV4 / (OUT_TOKEN + "_BLOCKED")
SUMMARY = f"PAD_Stream_{OUT_TOKEN}_Summary.json"
ARCH = f"{OUT_TOKEN}_Architecture_Contract.json"
HANDOFF = f"{OUT_TOKEN}_G1_Handoff_Contract.json"
DECISION = f"{OUT_TOKEN}_Decision_Contract.json"
GATES = f"{OUT_TOKEN}_Final_Gate_Matrix.csv"
MANIFEST = f"{OUT_TOKEN}_Artifact_Manifest.csv"

class GateError(RuntimeError):
    pass

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()

def gt(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()

def js(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    for row in rows:
        for k in row:
            if k not in fields:
                fields.append(k)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

def verify_manifest(directory: Path, filename: str) -> dict[str, str]:
    rows = csv_rows(directory / filename)
    if not rows:
        raise GateError(f"manifest_empty:{directory / filename}")
    found: dict[str, str] = {}
    for row in rows:
        p = directory / row["file"]
        if not p.is_file():
            raise GateError(f"manifest_missing:{p.name}")
        actual = sha256(p)
        if actual != row["sha256"]:
            raise GateError(f"manifest_sha:{p.name}")
        if p.stat().st_size != int(row["bytes"]):
            raise GateError(f"manifest_bytes:{p.name}")
        found[p.name] = actual
    return found

def bind_sha(path: Path, expected: str) -> None:
    if not path.is_file():
        raise GateError(f"missing:{path}")
    actual = sha256(path)
    if actual != expected:
        raise GateError(f"sha:{path.name}:{actual}:{expected}")

def selftest() -> None:
    assert EXPECTED_STREAMLINES == 1078
    assert EXPECTED_NXI == 201
    assert sum(EXPECTED_ROUTE_COUNTS.values()) == EXPECTED_STREAMLINES
    assert EXPECTED_EARLY_PROBES == [[75,80],[120,125],[40,45]]
    architecture = {
        "transport_clock": "may advance while flow_epoch_id is held",
        "flow_epoch": ["pressure", "Darcy", "Pollock", "TOF", "weights", "connectivity"],
        "late_time_evidence_bracket_days": [5, 15],
    }
    assert "connectivity" in architecture["flow_epoch"]
    print("POSTV16 GPU-HYB-G0 structural/integration self-test: PASS")

def main(project_root: Path, drive_root: Path) -> int:
    root = project_root.resolve()
    drive = drive_root.resolve()
    out = drive / OUT_REL
    staging = drive / STAGE_REL
    blocked = drive / BLOCK_REL
    stage = "preflight"
    gates: list[dict[str, Any]] = []

    def gate(name: str, cond: Any, detail: Any = None) -> None:
        ok = bool(cond)
        gates.append({"stage": stage, "gate": name, "pass": ok, "detail": "" if detail is None else repr(detail)})
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + ("" if detail is None else f" -- {detail}"), flush=True)
        if not ok:
            raise GateError(name)

    try:
        print("=" * 190)
        print("POSTV16-AV4-PIVOT-GPU-HYB-G0 — CADENCE-AWARE HYBRID BL-DP / CURRENT AV4 PIVOT INTEGRATION CONTRACT FREEZE")
        print("DESIGN / AUTHORITY BINDING ONLY. NO TRAINING. NO MODEL INFERENCE. NO PRESSURE/FLOW RECOMPUTATION. NO TRANSPORT ADVANCE.")
        print("=" * 190)

        stage = "repository_authority"
        gate("branch_exact", gt(root, "branch", "--show-current") == BRANCH, gt(root, "branch", "--show-current"))
        gate("parent_is_P_CAD_A2_commit", gt(root, "rev-parse", "HEAD^") == PARENT, gt(root, "rev-parse", "HEAD^"))
        gate("repository_clean", gt(root, "status", "--porcelain") == "")
        for fn, blob in [
            (PCAD_A2_RUNNER, PCAD_A2_BLOB),
            (E11_RUNNER, E11_RUNNER_BLOB),
            (E12_RUNNER, E12_RUNNER_BLOB),
            (E9_ADAPTER, E9_ADAPTER_BLOB),
        ]:
            p = root / fn
            gate(f"{Path(fn).stem}_present", p.is_file(), str(p))
            gate(f"{Path(fn).stem}_blob_exact", gt(root, "hash-object", str(p)) == blob,
                 gt(root, "hash-object", str(p)) if p.is_file() else "missing")

        stage = "P_CAD_A2_authority"
        a2dir = drive / PCAD_A2_REL
        gate("P_CAD_A2_output_exists", a2dir.is_dir(), str(a2dir))
        for fn in [PCAD_A2_SUMMARY, PCAD_A2_DECISION, PCAD_A2_GPU_PROTOCOL, PCAD_A2_MANIFEST]:
            gate(f"P_CAD_A2_artifact_present:{fn}", (a2dir / fn).is_file())
        verify_manifest(a2dir, PCAD_A2_MANIFEST)
        a2s = js(a2dir / PCAD_A2_SUMMARY)
        a2d = js(a2dir / PCAD_A2_DECISION)
        gate("P_CAD_A2_status_exact", a2s.get("status") == PCAD_A2_STATUS, a2s.get("status"))
        gate("late_strict_hold_exact_5", a2s.get("late_time_strict_longest_hold_days") == 5)
        gate("late_typical_hold_exact_15", a2s.get("late_time_typical_longest_hold_days") == 15)
        gate("production_cadence_unselected", a2s.get("production_pressure_refresh_cadence_selected") is False)
        gate("early_probe_pairs_exact", a2s.get("future_GPU_targeted_probe_pairs") == EXPECTED_EARLY_PROBES,
             a2s.get("future_GPU_targeted_probe_pairs"))
        gate("learned_pressure_not_reference_truth", a2s.get("learned_pressure_seed_can_define_reference_truth") is False)
        gate("GPU_early_probe_execution_still_locked", a2d.get("P_CAD_A3_GPU_targeted_probe_execution_authorized") is False)
        gate("Day405_to410_preserved", a2d.get("Day405_to_Day410_transport_remains_authorized_from_R7R10") is True)
        gate("P4_locked", a2d.get("P4_authorized") is False)

        stage = "Hybrid_BLDP_E11_authority"
        e11dir = drive / E11_REL
        gate("E11_R2_output_exists", e11dir.is_dir(), str(e11dir))
        for _, (fn, hs) in {
            "pilot": E11_PILOT, "audit": E11_AUDIT, "summary": E11_SUMMARY, "handoff": E11_HANDOFF
        }.items():
            gate(f"E11_R2_artifact_present:{fn}", (e11dir / fn).is_file())
            gate(f"E11_R2_artifact_sha:{fn}", sha256(e11dir / fn) == hs,
                 sha256(e11dir / fn) if (e11dir / fn).is_file() else "missing")
        e11s = js(e11dir / E11_SUMMARY[0])
        gate("E11_R2_status_PASS", str(e11s.get("status")).upper() == "PASS", e11s.get("status"))
        gate("E11_R2_streamline_count", int(e11s.get("streamline_count", -1)) == EXPECTED_STREAMLINES,
             e11s.get("streamline_count"))
        gate("E11_R2_transport_nodes", int(e11s.get("transport_nodes", -1)) == EXPECTED_NXI,
             e11s.get("transport_nodes"))
        gate("E11_R2_physical_time_100d", float(e11s.get("physical_time_days", -1.0)) == 100.0,
             e11s.get("physical_time_days"))
        gate("E11_R2_zero_unsafe", int(e11s.get("unsafe_learned_proposals_accepted", -1)) == 0,
             e11s.get("unsafe_learned_proposals_accepted"))
        gate("E11_R2_no_mapback", e11s.get("grid_mapback_performed") is False)

        with np.load(e11dir / E11_PILOT[0], allow_pickle=False) as z:
            required = [
                "physical_time_days","xi","xyz_m","tau_s","tau_end_s","weights_m3_s","producer",
                "streamline_id","route_code","route_label","saturation_100d"
            ]
            gate("E11_R2_pilot_required_arrays", all(k in z.files for k in required), sorted(z.files))
            gate("E11_R2_xyz_shape", tuple(z["xyz_m"].shape) == (EXPECTED_STREAMLINES, EXPECTED_NXI, 3),
                 z["xyz_m"].shape)
            gate("E11_R2_tau_shape", tuple(z["tau_s"].shape) == (EXPECTED_STREAMLINES, EXPECTED_NXI),
                 z["tau_s"].shape)
            route_code = np.asarray(z["route_code"])
            counts = {
                "HYBRID10_ACCEPT": int(np.sum(route_code == 10)),
                "HYBRID12_ACCEPT": int(np.sum(route_code == 12)),
                "EXACT_R2_FALLBACK": int(np.sum(route_code == 20)),
                "FULL_PHYSICS_SG7A_FALLBACK": int(np.sum(route_code == 30)),
            }
            gate("E11_R2_route_counts_exact", counts == EXPECTED_ROUTE_COUNTS, counts)

        stage = "Hybrid_BLDP_E12_mapback_authority"
        e12dir = drive / E12_REL
        gate("E12_R1_output_exists", e12dir.is_dir(), str(e12dir))
        for fn in [E12_SUMMARY, E12_PROTOCOL, E12_RESULTS]:
            gate(f"E12_R1_artifact_present:{fn}", (e12dir / fn).is_file())
        e12s = js(e12dir / E12_SUMMARY)
        e12p = js(e12dir / E12_PROTOCOL)
        e12r = js(e12dir / E12_RESULTS)
        gate("E12_R1_status_PASS", str(e12s.get("status")).upper() == "PASS", e12s.get("status"))
        gate("E12_R1_route_counts_exact", e12s.get("route_counts") == EXPECTED_ROUTE_COUNTS, e12s.get("route_counts"))
        gate("E12_R1_mapback_protocol_frozen", e12s.get("mapback_protocol_frozen") is True)
        gate("E12_R1_mapback_not_executed", e12s.get("mapback_performed") is False)
        gate("E12_R1_E13_authorized", e12s.get("E13_authorized") is True)
        gate("E12_R1_full_grid_plume_locked", e12s.get("full_grid_plume_authorized") is False)
        gate("E12_R1_operator_segment_intersection",
             e12p.get("operator_contract", {}).get("method") == "flow-weighted piecewise-linear segment/cell intersection accumulation",
             e12p.get("operator_contract", {}).get("method"))
        gate("E12_R1_unsupported_cells_NaN",
             e12p.get("operator_contract", {}).get("unsupported_cell_state") == "NaN")
        gate("E12_R1_no_unsupported_fill",
             e12p.get("operator_contract", {}).get("unsupported_fill_authorized") is False)
        gate("E12_R1_results_no_inference", e12r.get("training_or_inference_performed") is False)

        stage = "integration_contract_freeze"
        architecture = {
            "milestone": M,
            "status": PASS,
            "purpose": (
                "Bind the current AV4 pivot cadence authority to the already-certified heterogeneous Hybrid BL-DP "
                "streamline transport and conservative map-back lineage without executing new physics."
            ),
            "two_clock_architecture": {
                "transport_clock": {
                    "role": "GPU BL/Hybrid-DP transport may advance through intermediate transport times while reusing one frozen flow epoch.",
                    "independent_of_flow_refresh_clock": True,
                    "production_transport_step_or_output_interval_selected_here": False,
                },
                "flow_epoch_clock": {
                    "role": "A flow epoch is refreshed only as a complete coupled pressure/flow-network state.",
                    "flow_epoch_state_members": [
                        "exact/corrected pressure",
                        "conservative Darcy Qx/Qy/Qz",
                        "exact Pollock streamline geometry",
                        "terminal TOF",
                        "streamline volumetric weights",
                        "producer connectivity",
                    ],
                    "partial_pressure_only_refresh_is_not_the_production_semantics": True,
                },
            },
            "cadence_evidence": {
                "late_time_strict_empirical_hold_days": 5,
                "late_time_typical_empirical_hold_days": 15,
                "production_cadence_selected": False,
                "strict_10day_failure_drivers": a2s.get("strict_failure_drivers_at_10_days"),
                "typical_20day_failure_drivers": a2s.get("typical_failure_drivers_at_20_days"),
                "early_target_pairs": EXPECTED_EARLY_PROBES,
                "brute_force_Day30_to_Day365_five_day_sweep_authorized": False,
            },
            "hybrid_transport_authority": {
                "E11_R2_streamlines": EXPECTED_STREAMLINES,
                "E11_R2_nodes_per_streamline": EXPECTED_NXI,
                "E11_R2_route_counts": EXPECTED_ROUTE_COUNTS,
                "learned_proposals_are_screened": True,
                "screen_rejection_or_unsupported_path_uses_exact_or_full_physics_fallback": True,
                "zero_unsafe_learned_accepts_required": True,
                "reference_truth_may_not_be_defined_by_learned_prediction": True,
            },
            "mapback_authority": {
                "source": "V16E12-R1 / V15-SG7D1 lineage",
                "method": "flow-weighted piecewise-linear segment/cell intersection accumulation",
                "unsupported_cell_policy": "NaN / no fill",
                "route_labels_are_provenance_only": True,
                "full_grid_projection_authorized": False,
            },
            "future_reference_truth": {
                "pressure": "exact finite-volume pressure; learned seed may later accelerate but never define truth",
                "Darcy": "conservative exact Darcy face fluxes",
                "streamlines": "exact Pollock",
                "TOF": "exact pathwise time-of-flight",
                "transport": "screened Hybrid BL-DP proposal with exact/full-physics fallback authority",
            },
            "current_AV4_pivot_endpoint": {
                "authoritative_physical_day": 405,
                "Day405_to_Day410_transport_executed": False,
                "Day405_to_Day410_transport_remains_authorized": True,
                "P4_authorized": False,
            },
        }

        g1 = {
            "milestone": "POSTV16-AV4-PIVOT-GPU-HYB-G1",
            "name": "Controlled GPU Runtime / Existing 100-Day Hybrid BL-DP Single-State Replay Certification",
            "authorized": True,
            "purpose": (
                "Prove the GPU runtime, model/checkpoint loading, Hybrid routing, exact fallback, and current integration "
                "data interface on the already-certified E11-R2 100-day state before generating a new early-time trajectory."
            ),
            "must_bind": [
                "G0 integration contract",
                "P-CAD-A2 cadence authority",
                "E11-R2 pilot SHA",
                "E12-R1 map-back protocol",
                "unchanged Hybrid checkpoints/routing/screening authority",
            ],
            "execution_scope": {
                "GPU_model_inference": True,
                "new_pressure_solve": False,
                "Darcy_recompute": False,
                "Pollock_retrace": False,
                "TOF_recompute": False,
                "new_physical_time_advance": False,
                "streamline_to_grid_mapback_execution": False,
                "AV4_authoritative_state_mutation": False,
            },
            "required_replay_checks": [
                "1078 streamline / 201-node interface exact",
                "route eligibility and route counts preserve frozen semantics",
                "zero unsafe learned accepts",
                "fallback paths remain exact/full-physics authority",
                "GPU replay outputs are numerically consistent with the frozen E11-R2 reference under a predeclared replay comparison contract",
            ],
            "G2_authorization_on_PASS": (
                "Authorize construction of a cadence-aware contiguous early GPU BL/Hybrid-DP reference trajectory "
                "and execution of the frozen Day75-80, Day120-125, Day40-45 cadence probes."
            ),
        }

        decision = {
            "milestone": M,
            "status": PASS,
            "classification": "CADENCE_AUTHORITY_AND_CERTIFIED_HYBRID_SGSIM_TRANSPORT_LINEAGE_BOUND_G1_SINGLE_STATE_GPU_REPLAY_AUTHORIZED",
            "GPU_HYB_G1_single_state_replay_authorized": True,
            "GPU_HYB_G2_early_contiguous_trajectory_authorized": False,
            "GPU_HYB_G2_targeted_early_probe_execution_authorized": False,
            "production_pressure_refresh_cadence_selected": False,
            "brute_force_Day30_to_Day365_five_day_sweep_authorized": False,
            "Day405_to_Day410_transport_remains_authorized": True,
            "Day405_to_Day410_transport_executed": False,
            "P4_authorized": False,
            "recommended_next_action": (
                "Execute G1 on a GPU using only the frozen 100-day E11-R2 state to certify the runtime and integration "
                "interface. Do not build the early contiguous trajectory until G1 passes."
            ),
        }

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": decision["classification"],
            "repository_parent_P_CAD_A2_commit": PARENT,
            "source_P_CAD_A2_summary_sha256": sha256(a2dir / PCAD_A2_SUMMARY),
            "source_E11_R2_pilot_sha256": E11_PILOT[1],
            "source_E11_R2_summary_sha256": E11_SUMMARY[1],
            "source_E12_R1_summary_sha256": sha256(e12dir / E12_SUMMARY),
            "source_E12_R1_protocol_sha256": sha256(e12dir / E12_PROTOCOL),
            "late_time_evidence_bracket_days": [5, 15],
            "early_target_pairs": EXPECTED_EARLY_PROBES,
            "two_clock_architecture_frozen": True,
            "flow_epoch_is_full_pressure_flow_network_state": True,
            "Hybrid_BLDP_E11_R2_authority_bound": True,
            "conservative_mapback_protocol_bound": True,
            "GPU_HYB_G1_authorized": True,
            "GPU_HYB_G2_authorized": False,
            "training_executed": False,
            "model_inference_executed": False,
            "pressure_solve_executed": False,
            "Darcy_recomputation_executed": False,
            "Pollock_retracing_executed": False,
            "TOF_recomputation_executed": False,
            "transport_execution_executed": False,
            "authoritative_physics_state_mutated": False,
            "Day405_to_Day410_transport_executed": False,
            "Day405_to_Day410_transport_remains_authorized": True,
            "P4_authorized": False,
        }

        stage = "publication"
        gate("output_does_not_preexist", not out.exists(), str(out))
        if staging.exists():
            shutil.rmtree(staging)
        staging.mkdir(parents=True, exist_ok=False)
        (staging / ARCH).write_text(json.dumps(architecture, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (staging / HANDOFF).write_text(json.dumps(g1, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (staging / DECISION).write_text(json.dumps(decision, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (staging / SUMMARY).write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        write_csv(staging / GATES, gates)
        manifest_rows = []
        for p in sorted(staging.iterdir()):
            if p.is_file() and p.name != MANIFEST:
                manifest_rows.append({"file": p.name, "sha256": sha256(p), "bytes": p.stat().st_size})
        write_csv(staging / MANIFEST, manifest_rows)
        staging.rename(out)

        print("=" * 190)
        print(M, "PASS")
        print("Two-clock architecture frozen                    : True")
        print("Late-time evidence bracket (days)                : [5, 15]")
        print("Early target pairs                               :", EXPECTED_EARLY_PROBES)
        print("E11-R2 Hybrid SGSim pilot bound                  : True")
        print("E12-R1 conservative map-back protocol bound      : True")
        print("G1 controlled single-state GPU replay authorized : True")
        print("G2 early contiguous GPU trajectory authorized    : False")
        print("New physics / physical time advance executed     : False")
        print("Day405->Day410 remains authorized                : True")
        print("P4 authorized                                    : False")
        print("Output directory                                 :", out)
        print("=" * 190)
        return 0

    except Exception as exc:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        blocked.mkdir(parents=True, exist_ok=True)
        (blocked / f"{OUT_TOKEN}_Blocked_Report.json").write_text(json.dumps({
            "milestone": M,
            "status": BLOCK,
            "failed_stage": stage,
            "exception": repr(exc),
            "model_inference_executed": False,
            "transport_execution_executed": False,
            "authoritative_physics_state_mutated": False,
            "P4_authorized": False,
            "gates_completed": gates,
        }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
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
