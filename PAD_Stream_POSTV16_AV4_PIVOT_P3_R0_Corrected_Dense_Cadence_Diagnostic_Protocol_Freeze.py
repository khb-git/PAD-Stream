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

M = "POSTV16-AV4-PIVOT-P3-R0"
NAME = "Corrected Dense Cadence Diagnostic Protocol Freeze"
PASS = (
    "AV4PIVOTP3R0_CORRECTED_DENSE_CADENCE_DIAGNOSTIC_PROTOCOL_FREEZE_PASS_"
    "R32_RECURRENT_SEMANTICS_BOUND_NO_PHYSICS_EXECUTION"
)
BLOCK = "AV4PIVOTP3R0_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "4c365c7566b91f7754c12a9589d678b9c153e565"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"
BASE_AV3 = Path("post_v16") / RID / "POSTV16_AV3_Corey_Relperm_Heterogeneity"

GRID = [15, 50, 50]
NSL = 1078
NN = 201
NCV = 200
START_DAY = 365.0
END_DAY = 500.0
OBS_SPACING_DAYS = 5.0
OBS_DAYS = [float(x) for x in range(365, 501, 5)]
CANDIDATE_CADENCES_DAYS = [50.0, 5.0]
POLICIES = ["frozen flow", "50-day refresh", "5-day refresh"]

# Existing source-authority blobs.
SOURCE_BLOBS = {
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R33_Deferred_Cadence_Reactivation_and_Corrected_P3_Protocol_Design_Freeze.py":
        "cf9b518805091e297033be7ddf26a76603309706",
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R32_Independent_Recurrent_Operation_Closure_Audit.py":
        "435f5d6dcba38de7166e41ba9e081b6ef573edcf",
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R31_PostR30_Recurrent_FrozenFlow_Transport_Mapback_Certification.py":
        "c6307aa53109c4ae6c4a2f962e1fef86fbc8ea4a",
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R30_Atomic_Physical_Time_Commit_Accepted_AllCV_XY1_Candidate.py":
        "d75f469c4df3eef48d30bbbb3b1e1f667dcefc2e",
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R28_FrozenFlow_Transport_DeltaMapback_ResidualWell_Coupling_Protocol_Freeze.py":
        "90981a4fe0dc22bba270b12ab94b1bb4041d3eaa",
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R27_Day375_CapacityLimited_Residual_Transport_Temporal_Semantics_Design_Freeze.py":
        "c4c67c7349c6aefc2679178bfbeb80e6baa1ee97",
    "PAD_Stream_POSTV16_AV4_PIVOT_P0_Pressure_Refresh_Cadence_Diagnostic_Design_Freeze.py":
        "74342f6e770803acf66deeff80c62400fd8aa96f",
    "PAD_Stream_POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution.py":
        "79a8969233b72b4543edd382a0c3d1028c6dca09",
    "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py":
        "a127f8730a16e150713420ea547a8de6255550ef",
    "PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py":
        "0bbf98ed89cee9128ef1d313c321f9a401b4e9f0",
    "PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py":
        "890088c0c0fcab415a2c7351c5079ca8ee12bf82",
    "PAD_Stream_V15SG7A_Full_Physics_TOF_Transport.py":
        "a4dd47338e7a85f130a6a70d0a41211e38c655f8",
    "PAD_Stream_V16E36_Short_Adaptive_SGSim_Rollout_and_Early_Plume_Snapshot_Validation.py":
        "9ab4035c95a25bd61c649f86c82d88f059cef9e2",
    "PAD_Stream_V15SG2_Anisotropic_Transmissibility.py":
        "7242012d3e758472abc3ee7f543831b92d2cf419",
    "PAD_Stream_V15SG3_FiveSpot_Pressure_Solve.py":
        "66a379cd97ee9120f69e7e7e949171541e4918c3",
    "PAD_Stream_V15SG4_Conservative_Darcy_Fluxes.py":
        "8d49f88bdf55b0da087af2bed04e69967740e695",
    "PAD_Stream_V15SG5_Exact_Pollock_Streamlines.py":
        "9a0b64ea7e669904d0d9855ade1c6b052f05ecea",
    "PAD_Stream_V15SG6_TOF_Transport_Coordinates.py":
        "70ceda68e02894167958d753d88b4dbd694731ab",
}

# R33 authority.
R33_TOKEN = "POSTV16_AV4_PIVOT_P2_R6_R33"
R33_REL = BASE_AV4 / (R33_TOKEN + "_Deferred_Cadence_Reactivation_and_Corrected_P3_Protocol_Design_Freeze")
R33_SUMMARY = f"PAD_Stream_{R33_TOKEN}_Summary.json"
R33_PROTOCOL = f"{R33_TOKEN}_Corrected_P3_Protocol_Freeze.json"
R33_DECISION = f"{R33_TOKEN}_Decision_Contract.json"
R33_HANDOFF = f"{R33_TOKEN}_P3_R0_Handoff_Contract.json"
R33_MANIFEST = f"{R33_TOKEN}_Artifact_Manifest.csv"
R33_STATUS = (
    "AV4PIVOTP2R6R33_DEFERRED_REFRESH_CADENCE_REACTIVATION_CORRECTED_P3_PROTOCOL_"
    "DESIGN_FREEZE_PASS_NO_PHYSICS_EXECUTION"
)

# P0 metrics/architecture authority.
P0_REL = BASE_AV4 / "POSTV16_AV4_PIVOT_P0_Pressure_Refresh_Cadence_Diagnostic_Design_Freeze"
P0_ARCH = "POSTV16_AV4_PIVOT_P0_Diagnostic_Architecture.json"
P0_METRICS = "POSTV16_AV4_PIVOT_P0_Observable_Metric_Contract.json"
P0_MANIFEST = "POSTV16_AV4_PIVOT_P0_Artifact_Manifest.csv"

# R32 current repaired recurrent authority.
R32_TOKEN = "POSTV16_AV4_PIVOT_P2_R6_R32"
R32_REL = BASE_AV4 / (R32_TOKEN + "_Independent_Recurrent_Operation_Closure_Audit")
R32_SUMMARY = f"PAD_Stream_{R32_TOKEN}_Summary.json"
R32_CLOSURE = f"{R32_TOKEN}_AV4_Recurrent_Physics_Closure_Contract.json"
R32_MANIFEST = f"{R32_TOKEN}_Artifact_Manifest.csv"
R32_STATE_SHA = "07856a508db8ae6ba449e9e248bf8cdbc406eb0b4504471099b4b82f6048e0a6"

# Accepted Day365 exact flow epoch.
A2E_REL = BASE_AV4 / "POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution"
A2E_SUMMARY = "PAD_Stream_POSTV16_AV4_A2_E_Summary.json"
A2E_EPOCH = "POSTV16_AV4_A2_E_Refreshed_Flow_Epoch.npz"
A2E_MANIFEST = "POSTV16_AV4_A2_E_Artifact_Manifest.csv"
A2E_STATUS = (
    "AV4A2E_AV3CR0003_DAY365_SAME_TIME_SPATIAL_MOBILITY_PRESSURE_SATURATION_"
    "REFRESH_DARCY_POLLOCK_TOF_GEOMETRY_EXECUTION_PASS"
)

# Heterogeneous storage/constitutive authority.
A6E_REL = BASE_AV3 / "POSTV16_AV3_A6_E_Frozen_Checkpoint_LocalPV_R7D_Integration_Execution"
A6E_STATE = "POSTV16_AV3_A6_E_AV3CR0003_Integrated_State.npz"
A6E_MANIFEST = "POSTV16_AV3_A6_E_Artifact_Manifest.csv"
A6E_SHA = "f9e3a7bd8c6dcc43d522e0cb99a0cede2bd212fd570085b4faf82dc71af8f803"

OUT_TOKEN = "POSTV16_AV4_PIVOT_P3_R0"
OUT_REL = BASE_AV4 / (OUT_TOKEN + "_Corrected_Dense_Cadence_Diagnostic_Protocol_Freeze")
BLOCK_REL = BASE_AV4 / (OUT_TOKEN + "_BLOCKED")

SUMMARY = f"PAD_Stream_{OUT_TOKEN}_Summary.json"
AUTHORITY = f"{OUT_TOKEN}_Execution_Authority_Contract.json"
TIMESTEP = f"{OUT_TOKEN}_Atomic_Substep_and_Observation_Policy.json"
STATE_SCHEMA = f"{OUT_TOKEN}_Dense_State_and_Flow_Artifact_Schema.json"
METRICS = f"{OUT_TOKEN}_P3_P4_Metric_and_Cost_Contract.json"
EXEC_HANDOFF = f"{OUT_TOKEN}_P3_R1_Handoff_Contract.json"
DECISION = f"{OUT_TOKEN}_Decision_Contract.json"
GATE_MATRIX = f"{OUT_TOKEN}_Final_Gate_Matrix.csv"
MANIFEST = f"{OUT_TOKEN}_Artifact_Manifest.csv"


class GateError(RuntimeError):
    pass


def gt(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def js(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def csvr(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
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
    return (json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


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
    if not result:
        raise GateError(f"manifest_empty:{filename}")
    return result


def selftest() -> None:
    assert len(OBS_DAYS) == 28
    assert OBS_DAYS[0] == 365.0 and OBS_DAYS[-1] == 500.0
    assert CANDIDATE_CADENCES_DAYS == [50.0, 5.0]
    assert POLICIES == ["frozen flow", "50-day refresh", "5-day refresh"]
    assert NSL == 1078 and NN == 201 and NCV == 200
    print("POSTV16 AV4 PIVOT P3-R0 structural self-test: PASS")


def main(project_root: Path, drive_root: Path) -> int:
    root = project_root.resolve()
    drive = drive_root.resolve()
    out = drive / OUT_REL
    block_dir = drive / BLOCK_REL
    stage = "preflight"
    gates: list[dict[str, Any]] = []

    def gate(name: str, cond: Any, detail: Any = None) -> None:
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
        print("=" * 214)
        print("POSTV16-AV4-PIVOT-P3-R0 — CORRECTED DENSE CADENCE DIAGNOSTIC PROTOCOL FREEZE")
        print("=" * 214)
        print("DESIGN FREEZE ONLY. NO TRANSPORT, PRESSURE, DARCY, POLLOCK, TOF, MAPBACK, OR TIME ADVANCE.")
        print("5 DAYS REMAINS THE OBSERVATION SPACING — NOT THE REQUIRED INTERNAL TRANSPORT SUBSTEP.")
        print("P3-R1 MAY EXECUTE ONLY THE PROSPECTIVELY FROZEN ATOMIC CANDIDATE/GATE/COMMIT POLICY.")
        print()

        stage = "preexisting_state_firewall"
        gate("no_preexisting_PASS", not (out / SUMMARY).exists())
        gate("no_preexisting_BLOCK", not (block_dir / f"{OUT_TOKEN}_Blocked_Report.json").exists())

        stage = "repository_authority"
        branch = gt(root, "branch", "--show-current")
        parent = gt(root, "rev-parse", "HEAD^")
        dirty = gt(root, "status", "--porcelain")
        gate("branch_exact", branch == BRANCH, branch)
        gate("parent_exact", parent == PARENT, parent)
        gate("repository_clean", dirty == "", repr(dirty))
        for fn, expected in SOURCE_BLOBS.items():
            p = root / fn
            gate(f"{Path(fn).stem}_present", p.is_file(), str(p))
            actual = gt(root, "hash-object", str(p)) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_blob_exact", actual == expected, actual)

        stage = "R33_handoff_authority"
        r33d = drive / R33_REL
        r33m = manifest(r33d, R33_MANIFEST)
        r33s = js(r33d / R33_SUMMARY)
        r33p = js(r33d / R33_PROTOCOL)
        r33c = js(r33d / R33_DECISION)
        r33h = js(r33d / R33_HANDOFF)
        gate("R33_manifest_nonempty", len(r33m) > 0)
        gate("R33_status_exact", r33s.get("status") == R33_STATUS, r33s.get("status"))
        gate("R33_cadence_reactivated", r33s.get("AV4_deferred_cadence_obligation_reactivated") is True)
        gate("R33_old_P2_not_authority", r33s.get("old_P2_recovery_promoted_to_authority") is False)
        gate("R33_R32_SHA_exact", r33s.get("R32_authoritative_state_sha256") == R32_STATE_SHA)
        gate("R33_P3R0_authorized", r33c.get("P3_R0_design_freeze_authorized") is True)
        gate("R33_P3_physics_still_locked", r33c.get("P3_physics_execution_authorized") is False)
        gate("R33_handoff_design_only", r33h.get("design_freeze_only") is True)
        gate("R33_handoff_R32_semantics_required", r33h.get("must_use_R32_certified_recurrent_semantics") is True)
        gate("R33_handoff_A2E_start_required", r33h.get("must_use_A2E_Day365_start_flow_authority") is True)
        gate("R33_window_exact", r33p["unchanged_P0_contract"]["window_days"] == [365.0, 500.0])
        gate("R33_observation_days_exact", r33p["unchanged_P0_contract"]["observation_days"] == OBS_DAYS)
        gate("R33_candidates_exact", r33p["unchanged_P0_contract"]["candidate_cadences_days"] == CANDIDATE_CADENCES_DAYS)

        stage = "P0_metric_authority"
        p0d = drive / P0_REL
        p0m = manifest(p0d, P0_MANIFEST)
        p0a = js(p0d / P0_ARCH)
        p0metrics = js(p0d / P0_METRICS)
        gate("P0_manifest_nonempty", len(p0m) > 0)
        gate("P0_pipeline_exact",
             p0a["phase_P3"]["pipeline"] ==
             ["S(t)", "spatial mobility", "pressure", "Darcy flux", "Pollock", "TOF"])
        gate("P0_policy_set_exact", p0a["phase_P4"]["policies"] == POLICIES)
        gate("P0_no_preselected_cadence",
             p0a["phase_P4"]["selection_rule"] ==
             "accuracy-versus-cost evidence; no cadence preselected in P0")
        gate("P0_no_numeric_acceptance_threshold",
             p0metrics["P0_numeric_acceptance_thresholds"] ==
             "NONE; P0 freezes observables, not an arbitrary production cadence.")

        stage = "R32_recurrent_semantics_authority"
        r32d = drive / R32_REL
        r32m = manifest(r32d, R32_MANIFEST)
        r32s = js(r32d / R32_SUMMARY)
        r32close = js(r32d / R32_CLOSURE)
        gate("R32_manifest_nonempty", len(r32m) > 0)
        gate("R32_closed", r32s.get("AV4_recurrent_physics_closed") is True)
        gate("R32_state_SHA_exact", r32s.get("R30_committed_state_sha256") == R32_STATE_SHA)
        gate("R32_full_cartesian_primary",
             r32close["AV4_recurrent_physics_closure"]["restart_semantics"]["primary_recurrent_physical_state"]
             == "cartesian_component_mass_kg")
        gate("R32_future_refresh_whole_cartesian",
             r32close["AV4_recurrent_physics_closure"]["restart_semantics"]["future_refresh_input"]
             == "entire Cartesian component-mass inventory")

        stage = "Day365_start_authority"
        a2ed = drive / A2E_REL
        a2em = manifest(a2ed, A2E_MANIFEST)
        a2es = js(a2ed / A2E_SUMMARY)
        gate("A2E_status_exact", a2es.get("status") == A2E_STATUS, a2es.get("status"))
        gate("A2E_epoch_manifested", A2E_EPOCH in a2em)
        a2e_epoch_sha = a2em[A2E_EPOCH]
        a2e_epoch = a2ed / A2E_EPOCH
        gate("A2E_epoch_SHA_exact", a2e_epoch.is_file() and sha(a2e_epoch) == a2e_epoch_sha, a2e_epoch_sha)

        # Read only schema / identities; no physics computation.
        import numpy as np
        with np.load(a2e_epoch, allow_pickle=False) as z:
            a2e_keys = sorted(z.files)
            day365_shapes = {k: list(np.asarray(z[k]).shape) for k in z.files}
            canonical_day = float(np.asarray(z["canonical_day"]).reshape(()))
            physical_advance = bool(np.asarray(z["physical_time_advance"]).reshape(()))
            pi_rnn = bool(np.asarray(z["PI_RNN_inference"]).reshape(()))
        required_a2e = {
            "parent_component_mass_kg", "reconciled_saturation", "refreshed_pressure_psi",
            "Qx", "Qy", "Qz", "streamline_xyz_m", "streamline_tof_s",
            "streamline_weight_m3_s", "streamline_face_pressure_psi", "pore_volume_m3",
            "reference_gas_pressure_pa", "paired_porosity", "nw", "no", "krw_max", "kro_max",
            "xi", "tau_end_s", "canonical_day",
        }
        gate("A2E_required_start_arrays_present", required_a2e.issubset(set(a2e_keys)), sorted(required_a2e))
        gate("A2E_canonical_day_365", canonical_day == 365.0, canonical_day)
        gate("A2E_no_time_advance", physical_advance is False)
        gate("A2E_no_PI_RNN", pi_rnn is False)

        stage = "heterogeneous_state_authority"
        a6ed = drive / A6E_REL
        a6em = manifest(a6ed, A6E_MANIFEST)
        a6e = a6ed / A6E_STATE
        gate("A6E_state_manifest_SHA_exact", a6em.get(A6E_STATE) == A6E_SHA)
        gate("A6E_state_file_SHA_exact", a6e.is_file() and sha(a6e) == A6E_SHA)

        stage = "protocol_freeze"
        source_stack = [
            {"role": "recurrent temporal semantics", "file": "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R27_Day375_CapacityLimited_Residual_Transport_Temporal_Semantics_Design_Freeze.py", "blob": SOURCE_BLOBS["PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R27_Day375_CapacityLimited_Residual_Transport_Temporal_Semantics_Design_Freeze.py"]},
            {"role": "delta-mapback / residual-well coupling", "file": "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R28_FrozenFlow_Transport_DeltaMapback_ResidualWell_Coupling_Protocol_Freeze.py", "blob": SOURCE_BLOBS["PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R28_FrozenFlow_Transport_DeltaMapback_ResidualWell_Coupling_Protocol_Freeze.py"]},
            {"role": "accepted recurrence proof", "file": "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R31_PostR30_Recurrent_FrozenFlow_Transport_Mapback_Certification.py", "blob": SOURCE_BLOBS["PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R31_PostR30_Recurrent_FrozenFlow_Transport_Mapback_Certification.py"]},
            {"role": "independent recurrent closure", "file": "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R32_Independent_Recurrent_Operation_Closure_Audit.py", "blob": SOURCE_BLOBS["PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R32_Independent_Recurrent_Operation_Closure_Audit.py"]},
            {"role": "CV conservative transport/mapback", "file": "PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py", "blob": SOURCE_BLOBS["PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"]},
            {"role": "compressible/capillary EOS and storage", "file": "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py", "blob": SOURCE_BLOBS["PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"]},
            {"role": "exact transport physics", "file": "PAD_Stream_V15SG7A_Full_Physics_TOF_Transport.py", "blob": SOURCE_BLOBS["PAD_Stream_V15SG7A_Full_Physics_TOF_Transport.py"]},
            {"role": "conservative geometry/mapback", "file": "PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py", "blob": SOURCE_BLOBS["PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"]},
            {"role": "adaptive-step precedent", "file": "PAD_Stream_V16E36_Short_Adaptive_SGSim_Rollout_and_Early_Plume_Snapshot_Validation.py", "blob": SOURCE_BLOBS["PAD_Stream_V16E36_Short_Adaptive_SGSim_Rollout_and_Early_Plume_Snapshot_Validation.py"]},
        ]

        authority = {
            "milestone": M,
            "status": PASS,
            "repository_parent": PARENT,
            "R33_status": R33_STATUS,
            "R32_authoritative_state_sha256": R32_STATE_SHA,
            "A2E_Day365_flow_epoch_sha256": a2e_epoch_sha,
            "A6E_heterogeneous_state_sha256": A6E_SHA,
            "grid": GRID,
            "streamlines": NSL,
            "nodes_per_streamline": NN,
            "control_volumes_per_streamline": NCV,
            "source_stack": source_stack,
            "authority_hierarchy": [
                "full Cartesian component mass is the recurrent physical state",
                "within a frozen flow epoch, transport CV mass plus residual sidecar is a representation of the Cartesian state",
                "residual sidecar is not physically immobile and is not silently injected into CVs",
                "CV transport advances only represented transport coordinates",
                "mapback applies transport delta to Cartesian represented mass",
                "hard capacity / nonnegativity / saturation / source-sink / restart gates precede atomic time commit",
                "at a flow refresh, the entire Cartesian inventory is reprojected onto newly traced geometry",
            ],
        }

        timestep = {
            "milestone": M,
            "status": PASS,
            "observation_policy": {
                "start_day": START_DAY,
                "end_day": END_DAY,
                "observation_spacing_days": OBS_SPACING_DAYS,
                "observation_days": OBS_DAYS,
                "five_days_is_observation_spacing_not_internal_dt": True,
                "every_observation_day_must_be_hit_exactly": True,
            },
            "internal_atomic_step_policy": {
                "mode": "PROSPECTIVELY_FROZEN_DETERMINISTIC_ADAPTIVE_ATOMIC_STEPS",
                "nominal_dt_rule": (
                    "At each accepted parent state, compute the source-authentic transport CFL limit from the "
                    "frozen Day365 TOF geometry using the V16E36/SG7A wave-speed construction; nominal dt is "
                    "min(CFL_dt_days, remaining_days_to_next_5day_observation)."
                ),
                "trial_policy": (
                    "Execute a prospective candidate without mutating the accepted parent. Apply the complete "
                    "R27/R28/R31/R32 hard gate set. If rejected, halve dt deterministically and retry from the "
                    "same immutable parent."
                ),
                "retry_factor": 0.5,
                "maximum_retries_per_atomic_step": 8,
                "why_eight_retries": (
                    "This is frozen prospectively before execution and provides resolution below the historically "
                    "accepted ~0.0372-day recurrent step even when the first trial spans the remaining 5-day interval."
                ),
                "mutation_rule": "Only a candidate that passes every hard gate may be atomically committed.",
                "failure_rule": "Exhausted retry budget is a formal scientific/technical stop; no automatic physics change.",
                "observation_boundary_rule": "Clip nominal dt to the exact remaining time so accepted state lands exactly on the next observation day.",
            },
            "hard_gates_each_atomic_step": [
                "transport CV mass finite and nonnegative",
                "transport CV saturation within [0.20, 0.80]",
                "explicit injection / production component-mass ledger",
                "CV source-sink closure",
                "delta mapback global closure",
                "represented Cartesian candidate nonnegative",
                "residual sidecar unchanged within current frozen flow epoch",
                "Cartesian component mass nonnegative",
                "Cartesian pressure-capacity consistency",
                "Cartesian saturation bounds",
                "EOS/storage reconstruction",
                "global source-sink closure",
                "restart serialization/readback identity",
            ],
            "no_silent_runtime_changes": [
                "no support growth outside prospectively frozen operator semantics",
                "no pressure refresh during common frozen-flow trajectory generation",
                "no TOF retrace during common frozen-flow trajectory generation",
                "no residual clipping/discard/rescaling",
                "no model inference",
            ],
        }

        state_schema = {
            "milestone": M,
            "status": PASS,
            "common_dense_state_basis": {
                "count": 28,
                "days": OBS_DAYS,
                "per_day_state_file_pattern": "POSTV16_AV4_PIVOT_P3_R1_Day{DAY:04d}_Accepted_Dense_State.npz",
                "required_state_arrays": {
                    "physical_day": "scalar float64",
                    "cartesian_component_mass_kg": GRID,
                    "represented_cartesian_cell_mass_kg": GRID,
                    "grid_residual_component_mass_kg": GRID,
                    "cartesian_saturation": GRID,
                    "transport_CV_component_mass_kg": [NSL, NCV],
                    "transport_CV_saturation": [NSL, NCV],
                    "frozen_flow_epoch_day": "scalar float64 (=365)",
                    "streamline_xyz_m": [NSL, NN, 3],
                    "streamline_tof_s": [NSL, NN],
                    "streamline_weight_m3_s": [NSL],
                    "reference_gas_pressure_pa": "scalar float64",
                    "cumulative_injected_component_mass_kg": "scalar float64",
                    "cumulative_produced_component_mass_kg": "scalar float64",
                },
                "restartable": True,
                "manifested": True,
            },
            "exact_diagnostic_flow_fields": {
                "per_day_flow_file_pattern": "POSTV16_AV4_PIVOT_P3_R1_Day{DAY:04d}_Exact_Flow_Diagnostic.npz",
                "required_arrays": {
                    "diagnostic_day": "scalar float64",
                    "saturation": GRID,
                    "lambda_total": GRID,
                    "pressure_psi": GRID,
                    "Qx": "source SG4 x-face shape",
                    "Qy": "source SG4 y-face shape",
                    "Qz": "source SG4 z-face shape",
                    "streamline_xyz_m": "source SG5/SG6 exact traced shape",
                    "streamline_tof_s": "same shape first two axes as streamline_xyz_m",
                    "streamline_weight_m3_s": "one per exact diagnostic streamline",
                    "tau_end_s": "one per exact diagnostic streamline",
                },
                "diagnostic_only_no_transport_feedback": True,
            },
            "consolidated_outputs": [
                "POSTV16_AV4_PIVOT_P3_R1_Dense_State_Audit.csv",
                "POSTV16_AV4_PIVOT_P3_R1_Exact_Flow_Diagnostic_Metrics.csv",
                "POSTV16_AV4_PIVOT_P3_R1_Atomic_Substep_Audit.csv",
                "POSTV16_AV4_PIVOT_P3_R1_Artifact_Manifest.csv",
            ],
        }

        metric_contract = {
            "milestone": M,
            "status": PASS,
            "P3_exact_reference_metrics_inherited_from_P0": p0metrics,
            "P3_timing_boundaries": {
                "common_transport_generation_timing": (
                    "Record separately for engineering/runtime diagnosis; exclude from cadence-policy refresh cost "
                    "because the same common dense transport history is shared by all three diagnostic policies."
                ),
                "per_observation_exact_refresh_timing_includes": [
                    "spatial mobility construction",
                    "pressure solve",
                    "Darcy flux construction and conservation audit",
                    "Pollock tracing",
                    "TOF database rebuild",
                ],
                "per_observation_exact_refresh_timing_excludes": [
                    "Drive/repository I/O",
                    "artifact serialization",
                    "plotting",
                    "common transport-history generation",
                ],
            },
            "P4_policy_mapping": {
                "frozen flow": {
                    "refresh_days": [365.0],
                    "stale_reference_rule": "Use the Day365 exact diagnostic flow field for all later observation days.",
                },
                "50-day refresh": {
                    "refresh_days": [365.0, 415.0, 465.0],
                    "stale_reference_rule": "At each observation day, use the most recent exact diagnostic field at or before that day from the 50-day schedule.",
                },
                "5-day refresh": {
                    "refresh_days": OBS_DAYS,
                    "stale_reference_rule": "At every observation day use that day's exact diagnostic field; diagnostic staleness is zero by construction.",
                },
            },
            "P4_accuracy_reference": "Exact P3 diagnostic field at the current observation day.",
            "P4_metrics": {
                "pressure": ["relative_L2", "Linf_psi", "producer_cell_pressure_change"],
                "darcy": ["face_flux_relative_L2", "face_flux_Linf", "local_conservation_residual", "global_conservation_mismatch"],
                "streamlines": ["producer_capture_count", "RMS_node_displacement_m", "maximum_node_displacement_m", "endpoint_displacement_m"],
                "tof": ["relative_L2", "weighted_mean_shift_days", "weighted_P50_shift_days", "weighted_P90_shift_days"],
                "compute": ["pressure_refresh_s", "Darcy_s", "Pollock_s", "TOF_s", "total_refresh_s"],
            },
            "P4_selection_rule": (
                "Accuracy-versus-refresh-cost evidence only. No cadence is preselected. P3-R1 does not select the "
                "cadence; it only creates exact common-state and exact diagnostic authority."
            ),
        }

        handoff = {
            "milestone": "POSTV16-AV4-PIVOT-P3-R1",
            "name": "Corrected Dense Frozen-Flow Trajectory + Exact 5-Day Flow-Diagnostic Sweep Execution",
            "authorized": True,
            "execution": True,
            "must_bind_P3_R0_status": PASS,
            "must_bind_repository_parent_to_P3_R0_commit": True,
            "must_bind_A2E_Day365_flow_epoch_SHA": a2e_epoch_sha,
            "must_bind_R32_authoritative_state_SHA": R32_STATE_SHA,
            "must_use_28_observation_days_exact": OBS_DAYS,
            "must_use_atomic_substep_policy_exact": True,
            "must_publish_all_28_accepted_dense_states": True,
            "must_publish_all_28_exact_flow_diagnostics": True,
            "must_publish_restart_and_mass_gate_audits": True,
            "must_not_select_cadence": True,
            "must_not_execute_P4": True,
            "must_not_train_or_run_ML": True,
            "old_P2_recovery_is_not_execution_state_authority": True,
        }

        classification = (
            "P3_R0_CORRECTED_DENSE_TRAJECTORY_AND_EXACT_FLOW_DIAGNOSTIC_PROTOCOL_FROZEN_"
            "ATOMIC_ADAPTIVE_SUBSTEPS_R32_SEMANTICS_A2E_DAY365_START_P3_R1_EXECUTION_AUTHORIZED"
        )

        decision = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "P3_R0_complete": True,
            "P3_R1_authorized": True,
            "P3_R1_execution_authorized": True,
            "P3_R1_physics_execution_authorized": True,
            "P4_authorized": False,
            "P5_authorized": False,
            "periodic_cadence_selected_now": False,
            "candidate_cadences_days": CANDIDATE_CADENCES_DAYS,
            "common_transport_flow_epoch_day": 365.0,
            "five_day_spacing_is_observation_not_internal_dt": True,
            "old_P2_recovery_promoted_to_authority": False,
            "ML_execution_authorized": False,
        }

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": classification,
            "A2E_Day365_flow_epoch_sha256": a2e_epoch_sha,
            "R32_authoritative_state_sha256": R32_STATE_SHA,
            "observation_start_day": START_DAY,
            "observation_end_day": END_DAY,
            "observation_spacing_days": OBS_SPACING_DAYS,
            "observation_count": len(OBS_DAYS),
            "candidate_cadences_days": CANDIDATE_CADENCES_DAYS,
            "policy_set": POLICIES,
            "internal_substep_policy": "deterministic adaptive atomic candidate/gate/commit",
            "internal_retry_factor": 0.5,
            "internal_max_retries": 8,
            "common_transport_flow_epoch_day": 365.0,
            "diagnostic_refresh_feedback_to_transport": False,
            "periodic_cadence_selected_now": False,
            "P3_R1_authorized": True,
            "P3_R1_execution_authorized": True,
            "P4_authorized": False,
            "P5_authorized": False,
            "physics_execution_executed": False,
            "state_mutation_executed": False,
            "physical_time_advance_executed": False,
        }

        out.mkdir(parents=True, exist_ok=False)
        files = {
            SUMMARY: jb(summary),
            AUTHORITY: jb(authority),
            TIMESTEP: jb(timestep),
            STATE_SCHEMA: jb(state_schema),
            METRICS: jb(metric_contract),
            EXEC_HANDOFF: jb(handoff),
            DECISION: jb(decision),
            GATE_MATRIX: csvb(gates),
        }
        for name, data in files.items():
            (out / name).write_bytes(data)

        rows = []
        for p in sorted(out.iterdir()):
            if p.is_file():
                rows.append({"file": p.name, "sha256": sha(p), "bytes": p.stat().st_size})
        (out / MANIFEST).write_bytes(csvb(rows))

        print()
        print("=" * 214)
        print(M, "PASS")
        print("Classification                              :", classification)
        print("Day365 A2E flow epoch SHA256                :", a2e_epoch_sha)
        print("R32 authoritative state SHA256              :", R32_STATE_SHA)
        print("Observation states                          :", len(OBS_DAYS), "(Day365..500 every 5d)")
        print("Internal dt                                 : deterministic adaptive atomic steps")
        print("Diagnostic refresh feeds transport          : False")
        print("P3-R1 corrected execution authorized        : True")
        print("P4 cadence comparison authorized            : False")
        print("Cadence selected                            : False")
        print("=" * 214)
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
                "P3_R1_authorized": False,
                "P4_authorized": False,
                "periodic_cadence_selected_now": False,
                "state_mutation_executed": False,
                "physical_time_advance_executed": False,
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
