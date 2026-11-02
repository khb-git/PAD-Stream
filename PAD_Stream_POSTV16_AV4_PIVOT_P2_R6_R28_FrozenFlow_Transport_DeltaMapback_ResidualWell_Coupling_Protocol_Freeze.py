#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, hashlib, importlib.util, io, json, subprocess, sys
from pathlib import Path
from typing import Any
import numpy as np

M = "POSTV16-AV4-PIVOT-P2-R6-R28"
NAME = "Post-Day375 Frozen-Flow Transport Delta-Mapback / Residual-Well Coupling Protocol Freeze"
PASS = "AV4PIVOTP2R6R28_FROZEN_FLOW_TRANSPORT_DELTA_MAPBACK_RESIDUAL_WELL_COUPLING_PROTOCOL_FREEZE_PASS_NO_EXECUTION"
BLOCK = "AV4PIVOTP2R6R28_TECHNICAL_OR_AUTHORITY_BLOCK"

BRANCH = "postv16-av4-pivot"
PARENT = "de6036ea343f1096eb5b2abcce895bd84d372979"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
BASE = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

GRID = (15, 50, 50)
NCELL = 37500
NSL = 1078
NN = 201
NCV = 200
DAY = 375.0
DAY_TO_S = 86400.0

# Frozen well geometry from the source-authentic R2 transport authority.
INJECTOR_I = 24
INJECTOR_J = 24
COMPLETION_K = tuple(range(5, 10))
PRODUCERS = {
    "PROD_SW": {"i": 4, "j": 4},
    "PROD_SE": {"i": 45, "j": 4},
    "PROD_NW": {"i": 4, "j": 45},
    "PROD_NE": {"i": 45, "j": 45},
}
INJECTOR_MASS_RATE_KG_DAY = 500000.0

# --------------------------------------------------------------------------------------------------
# R27 temporal-semantics authority.
# --------------------------------------------------------------------------------------------------

R27_REL = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R27_"
    "Day375_CapacityLimited_Residual_Transport_Temporal_Semantics_Design_Freeze"
)
R27_SUMMARY = "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R27_Summary.json"
R27_SEMANTICS = "POSTV16_AV4_PIVOT_P2_R6_R27_Residual_Transport_Temporal_Semantics_Contract.json"
R27_DECISION = "POSTV16_AV4_PIVOT_P2_R6_R27_Decision_Contract.json"
R27_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R27_Artifact_Manifest.csv"
R27_STATUS = (
    "AV4PIVOTP2R6R27_DAY375_CAPACITY_LIMITED_RESIDUAL_TRANSPORT_"
    "TEMPORAL_SEMANTICS_DESIGN_FREEZE_PASS_NO_EXECUTION"
)
R27_CLASSIFICATION = (
    "R6R27_RESIDUAL_IS_DEFERRED_CARTESIAN_RESERVE_DURING_CURRENT_FROZEN_FLOW_EPOCH_"
    "NOT_PHYSICAL_IMMOBILE_R28_DELTA_MAPBACK_AND_WELL_COUPLING_DESIGN_NEXT"
)

# --------------------------------------------------------------------------------------------------
# R26 acceptance / exact state.
# --------------------------------------------------------------------------------------------------

R26_REL = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R26_"
    "Day375_CapacityLimited_SplitState_Restart_Representation_Closure_and_Acceptance_Audit"
)
R26_ACCEPTANCE = "POSTV16_AV4_PIVOT_P2_R6_R26_Day375_SplitState_Acceptance_Contract.json"
R26_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R26_Artifact_Manifest.csv"

R25R3_REL = BASE / (
    "POSTV16_AV4_PIVOT_P2_R6_R25_R3_"
    "Controlled_Day375_CapacityLimited_ExactSupport_SplitState_"
    "Reprojection_Execution_Stage2_PresolveOff"
)
R25R3_STATE = "POSTV16_AV4_PIVOT_P2_R6_R25_R3_CapacityLimited_SplitState_Day375.npz"
R25R3_MANIFEST = "POSTV16_AV4_PIVOT_P2_R6_R25_R3_Artifact_Manifest.csv"
R25R3_STATE_SHA256 = "9893e2476bce1d46213cdd1304e60ad93b49ea285e084d06743a2ffab25f721f"

R22_EPOCH_SHA256 = "7f030fd3676eb3b61bc7f341dff8cb82659e87e210640a9488bf6fb15e7bd80e"
PRESSURE_EPOCH_SHA256 = "99d73cab1d33191a68578f29d3c03f9fac07ed77c39e124cc8eb5e5bf75aa84d"

# --------------------------------------------------------------------------------------------------
# Exact repository source authorities.
# --------------------------------------------------------------------------------------------------

R27_RUNNER = (
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R27_"
    "Day375_CapacityLimited_Residual_Transport_Temporal_Semantics_Design_Freeze.py"
)
R27_BLOB = "c4c67c7349c6aefc2679178bfbeb80e6baa1ee97"

R26_RUNNER = (
    "PAD_Stream_POSTV16_AV4_PIVOT_P2_R6_R26_"
    "Day375_CapacityLimited_SplitState_Closure_Acceptance_Audit.py"
)
R26_BLOB = "f72a6d2d9184dd287df3aa589a31fda0567503f4"

E37A = "PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB = "0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"

R2 = "PAD_Stream_V16E35_R2_Source_Conservative_Transport_Capillary_Split_First_Controlled_Transition.py"
R2_BLOB = "a127f8730a16e150713420ea547a8de6255550ef"

SG7D = "PAD_Stream_V15SG7D_Conservative_Streamline_Grid_MapBack.py"
SG7D_BLOB = "890088c0c0fcab415a2c7351c5079ca8ee12bf82"

SG7A = "PAD_Stream_V15SG7A_Full_Physics_TOF_Transport.py"
SG7A_BLOB = "a4dd47338e7a85f130a6a70d0a41211e38c655f8"

E36 = "PAD_Stream_V16E36_Short_Adaptive_SGSim_Rollout_and_Early_Plume_Snapshot_Validation.py"
E36_BLOB = "9ab4035c95a25bd61c649f86c82d88f059cef9e2"

SOURCE_BLOBS = {
    R27_RUNNER: R27_BLOB,
    R26_RUNNER: R26_BLOB,
    E37A: E37A_BLOB,
    R2: R2_BLOB,
    SG7D: SG7D_BLOB,
    SG7A: SG7A_BLOB,
    E36: E36_BLOB,
}

OUT_TOKEN = "POSTV16_AV4_PIVOT_P2_R6_R28"
OUT_REL = BASE / (
    OUT_TOKEN
    + "_FrozenFlow_Transport_DeltaMapback_ResidualWell_Coupling_Protocol_Freeze"
)
BLOCK_REL = BASE / (OUT_TOKEN + "_BLOCKED")


class GateError(RuntimeError):
    pass


def gt(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def js(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def csvr(path: Path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def csvb(rows: list[dict[str, Any]]) -> bytes:
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


def jb(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True) + "\n").encode("utf-8")


def manifest(directory: Path, filename: str) -> dict[str, str]:
    rows = csvr(directory / filename)
    out: dict[str, str] = {}
    for row in rows:
        p = directory / row["file"]
        if not p.is_file():
            raise GateError(f"manifest_missing:{p.name}")
        if sha(p) != row["sha256"]:
            raise GateError(f"manifest_sha:{p.name}")
        if p.stat().st_size != int(row["bytes"]):
            raise GateError(f"manifest_bytes:{p.name}")
        out[p.name] = row["sha256"]
    return out


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError(f"cannot_load:{path}")
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def selftest() -> None:
    assert OUT_REL.name.startswith(OUT_TOKEN + "_")
    assert len(COMPLETION_K) == 5
    assert len(PRODUCERS) == 4

    protocol = {
        "absolute_mapback_forbidden": True,
        "delta_mapback_required": True,
        "residual_direct_well_exchange": False,
        "represented_grid_candidate_nonnegative_gate": True,
        "physical_time_commit_in_candidate_execution": False,
    }
    assert protocol["absolute_mapback_forbidden"] is True
    assert protocol["delta_mapback_required"] is True
    assert protocol["residual_direct_well_exchange"] is False
    assert protocol["physical_time_commit_in_candidate_execution"] is False

    print("POSTV16 AV4 PIVOT P2-R6-R28 structural self-test: PASS")


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
        # ------------------------------------------------------------------------------------------
        # Immutable one-shot firewall.
        # ------------------------------------------------------------------------------------------
        stage = "preexisting_state_firewall"

        gate(
            "no_preexisting_R28_PASS",
            not (out / f"PAD_Stream_{OUT_TOKEN}_Summary.json").exists(),
        )
        gate(
            "no_preexisting_R28_BLOCK",
            not (block_dir / f"{OUT_TOKEN}_Blocked_Report.json").exists(),
        )

        # ------------------------------------------------------------------------------------------
        # Repository authority.
        # ------------------------------------------------------------------------------------------
        stage = "repository_authority"

        gate("branch_exact", gt(root, "branch", "--show-current") == BRANCH)
        gate("parent_is_R27_commit", gt(root, "rev-parse", "HEAD^") == PARENT)
        gate("repository_clean", gt(root, "status", "--porcelain") == "")

        for filename, expected in SOURCE_BLOBS.items():
            p = root / filename
            gate(f"{Path(filename).stem}_present", p.is_file(), str(p))
            actual = gt(root, "hash-object", str(p)) if p.is_file() else "missing"
            gate(f"{Path(filename).stem}_blob_exact", actual == expected, actual)

        # ------------------------------------------------------------------------------------------
        # R27 temporal-semantics authority.
        # ------------------------------------------------------------------------------------------
        stage = "R27_temporal_semantics_authority"

        r27 = drive / R27_REL
        manifest(r27, R27_MANIFEST)
        s27 = js(r27 / R27_SUMMARY)
        t27 = js(r27 / R27_SEMANTICS)
        d27 = js(r27 / R27_DECISION)

        gate("R27_status_exact", s27.get("status") == R27_STATUS, s27.get("status"))
        gate(
            "R27_classification_exact",
            s27.get("classification") == R27_CLASSIFICATION,
            s27.get("classification"),
        )
        gate("R27_state_SHA_exact", s27.get("accepted_state_sha256") == R25R3_STATE_SHA256)
        gate("R27_residual_not_physically_immobile", s27.get("residual_physical_immobility_claim") is False)
        gate(
            "R27_residual_excluded_from_current_streamline_operator",
            s27.get("residual_excluded_from_current_streamline_advective_operator") is True,
        )
        gate(
            "R27_residual_epoch_frozen",
            s27.get("residual_epoch_frozen_during_transport_coordinate_solve") is True,
        )
        gate("R27_future_delta_mapback_required", s27.get("future_delta_mapback_required") is True)

        within = t27.get("within_current_frozen_flow_epoch", {})
        gate("R27_absolute_CV_state_cannot_replace_grid", within.get("absolute_CV_state_may_not_replace_cartesian_state") is True)
        gate("R27_delta_update_required", within.get("future_cartesian_update_must_be_delta_based") is True)
        gate("R27_residual_no_silent_CV_injection", within.get("residual_may_not_be_silently_injected_into_CVs") is True)

        well_guard = t27.get("well_source_sink_guard", {})
        gate(
            "R27_well_overlap_quantification_required",
            well_guard.get("residual_well_overlap_must_be_quantified_before_transport_execution") is True,
        )

        gate("R28_authorized", d27.get("P2_R6_R28_authorized") is True)
        gate("R28_design_only", d27.get("P2_R6_R28_design_only") is True)
        gate("R28_execution_not_authorized", d27.get("P2_R6_R28_execution_authorized") is False)
        gate("R28_residual_injector_audit_required", d27.get("R28_must_quantify_residual_in_injector_cells") is True)
        gate("R28_residual_producer_audit_required", d27.get("R28_must_quantify_residual_in_producer_cells") is True)
        gate("R28_delta_mapback_freeze_required", d27.get("R28_must_freeze_conservative_CV_delta_to_grid_mapback") is True)
        gate("R28_well_ledger_freeze_required", d27.get("R28_must_freeze_explicit_injection_production_mass_ledger") is True)
        gate("R28_capacity_gate_freeze_required", d27.get("R28_must_freeze_precommit_cell_capacity_gate") is True)

        # ------------------------------------------------------------------------------------------
        # R26 accepted state authority.
        # ------------------------------------------------------------------------------------------
        stage = "R26_R25R3_state_authority"

        r26 = drive / R26_REL
        manifest(r26, R26_MANIFEST)
        a26 = js(r26 / R26_ACCEPTANCE)

        gate("R26_accepted_state_SHA_exact", a26.get("accepted_state_sha256") == R25R3_STATE_SHA256)
        gate("R26_state_not_rewritten", a26.get("state_rewritten_by_R26") is False)
        gate("R26_primary_cartesian_authority", a26.get("primary_recurrent_authority") == "cartesian_component_mass_kg")

        r25 = drive / R25R3_REL
        m25 = manifest(r25, R25R3_MANIFEST)
        state_path = r25 / R25R3_STATE
        gate("R25R3_state_manifest_SHA_exact", m25.get(R25R3_STATE) == R25R3_STATE_SHA256)
        gate("R25R3_state_file_SHA_exact", sha(state_path) == R25R3_STATE_SHA256)

        with np.load(state_path, allow_pickle=False) as z:
            grid_mass = np.asarray(z["cartesian_component_mass_kg"], dtype=np.float64)
            represented_grid = np.asarray(z["represented_cartesian_cell_mass_kg"], dtype=np.float64)
            residual_grid = np.asarray(z["grid_residual_component_mass_kg"], dtype=np.float64)
            cv_mass = np.asarray(z["transport_CV_component_mass_kg"], dtype=np.float64)
            cv_sat = np.asarray(z["transport_CV_saturation"], dtype=np.float64)
            edge_cell = np.asarray(z["exact_support_edge_cell"], dtype=np.int64).reshape(-1)
            xyz = np.asarray(z["streamline_xyz_m"], dtype=np.float64)
            tof_s = np.asarray(z["streamline_tof_s"], dtype=np.float64)
            weights_m3_s = np.asarray(z["streamline_weight_m3_s"], dtype=np.float64)
            producer_labels = np.asarray(z["producer_labels"]).astype("U32")
            pressure_psi = np.asarray(z["refreshed_pressure_psi"], dtype=np.float64)
            p_ref = float(np.asarray(z["reference_gas_pressure_pa"]).reshape(()))
            r22_sha = str(np.asarray(z["source_R22_flow_epoch_sha256"]).reshape(()))
            pressure_sha = str(np.asarray(z["source_pressure_epoch_sha256"]).reshape(()))

        gate(
            "accepted_state_shapes_exact",
            grid_mass.shape == GRID
            and represented_grid.shape == GRID
            and residual_grid.shape == GRID
            and cv_mass.shape == (NSL, NCV)
            and cv_sat.shape == (NSL, NCV)
            and xyz.shape == (NSL, NN, 3)
            and tof_s.shape == (NSL, NN)
            and weights_m3_s.shape == (NSL,),
        )
        gate("R22_source_SHA_exact", r22_sha == R22_EPOCH_SHA256)
        gate("pressure_source_SHA_exact", pressure_sha == PRESSURE_EPOCH_SHA256)
        gate(
            "accepted_grid_partition_exact",
            float(np.max(np.abs(grid_mass - represented_grid - residual_grid))) <= 1e-6,
        )

        # ------------------------------------------------------------------------------------------
        # Exact well/residual overlap audit.
        # ------------------------------------------------------------------------------------------
        stage = "residual_well_overlap_audit"

        s0_mask = np.zeros(NCELL, dtype=bool)
        s0_mask[np.unique(edge_cell)] = True
        s0_mask = s0_mask.reshape(GRID)

        rows: list[dict[str, Any]] = []

        def append_completion(well: str, role: str, k: int, j: int, i: int) -> None:
            total = float(grid_mass[k, j, i])
            represented = float(represented_grid[k, j, i])
            residual = float(residual_grid[k, j, i])
            rows.append({
                "well": well,
                "role": role,
                "k": int(k),
                "j": int(j),
                "i": int(i),
                "in_R22_S0": bool(s0_mask[k, j, i]),
                "cartesian_component_mass_kg": total,
                "represented_component_mass_kg": represented,
                "residual_component_mass_kg": residual,
                "residual_fraction_of_cell_component_mass": (
                    residual / total if total > 0.0 else 0.0
                ),
            })

        for k in COMPLETION_K:
            append_completion("INJECTOR", "injector", k, INJECTOR_J, INJECTOR_I)

        for name, loc in PRODUCERS.items():
            for k in COMPLETION_K:
                append_completion(name, "producer", k, int(loc["j"]), int(loc["i"]))

        injector_residual = float(sum(r["residual_component_mass_kg"] for r in rows if r["role"] == "injector"))
        producer_residual = float(sum(r["residual_component_mass_kg"] for r in rows if r["role"] == "producer"))
        active_well_residual = injector_residual + producer_residual
        total_residual = float(np.sum(residual_grid))

        injector_total = float(sum(r["cartesian_component_mass_kg"] for r in rows if r["role"] == "injector"))
        producer_total = float(sum(r["cartesian_component_mass_kg"] for r in rows if r["role"] == "producer"))

        gate("well_completion_count_exact_25", len(rows) == 25, len(rows))
        gate("well_overlap_values_finite", all(np.isfinite(float(r["residual_component_mass_kg"])) for r in rows))
        gate("well_residual_nonnegative", min(float(r["residual_component_mass_kg"]) for r in rows) >= -1e-10)
        gate("well_total_mass_nonnegative", min(float(r["cartesian_component_mass_kg"]) for r in rows) >= -1e-10)

        # ------------------------------------------------------------------------------------------
        # Bind exact implementation functions and nominal dt rule.
        # ------------------------------------------------------------------------------------------
        stage = "transport_delta_mapback_source_binding"

        e37a = load_module(root / E37A, "r28_e37a")
        r2 = load_module(root / R2, "r28_r2")
        sg7d = load_module(root / SG7D, "r28_sg7d")
        sg7a = load_module(root / SG7A, "r28_sg7a")

        gate("E37A_component_mass_advance_present", callable(getattr(e37a, "advance_component_mass_control_volumes", None)))
        gate("E37A_delta_mapback_present", callable(getattr(e37a, "map_control_volume_increment_to_grid", None)))
        gate("E37A_producer_ledger_present", callable(getattr(e37a, "producer_rows_from_flux", None)))
        gate("R2_mass_inversion_present", callable(getattr(r2, "_invert_incremental_sg_from_mass", None)))
        gate("SG7D_subsegment_operator_present", callable(getattr(sg7d, "build_subsegment_operator", None)))

        xi_faces = np.linspace(0.0, 1.0, NCV + 1, dtype=np.float64)
        dxi = float(xi_faces[1] - xi_faces[0])
        scan = np.linspace(float(sg7a.S_INITIAL), float(sg7a.S_INJECTED), 4001)
        max_df = float(np.max(np.abs(np.asarray(sg7a.df_dS(scan), dtype=np.float64))))
        u_face = np.asarray(sg7a.u_dimensionless(xi_faces), dtype=np.float64)
        max_wave_speed = float(np.max(u_face) * max_df)
        dtD_cfl = float(sg7a.CFL * dxi / (max_wave_speed + sg7a.EPS))
        fastest_tau_days = float(np.min(tof_s[:, -1] / DAY_TO_S))
        nominal_dt_days = float(dtD_cfl * fastest_tau_days)

        gate("nominal_dt_finite_positive", np.isfinite(nominal_dt_days) and nominal_dt_days > 0.0, nominal_dt_days)
        gate("nominal_dt_subday", nominal_dt_days < 0.10, nominal_dt_days)

        # Exact current geometry closure.
        op = sg7d.build_subsegment_operator(
            xyz,
            tof_s / DAY_TO_S,
            weights_m3_s * DAY_TO_S,
        )
        geometry = e37a.build_control_volume_geometry(
            r2,
            op,
            pressure_psi,
            p_ref,
            NSL,
            NCV,
        )
        expected_cv_pv = weights_m3_s[:, None] * DAY_TO_S * np.diff(tof_s / DAY_TO_S, axis=1)
        cv_pv = np.asarray(geometry["cv_pv_m3"], dtype=np.float64)
        cv_pv_rel = float(np.linalg.norm((cv_pv - expected_cv_pv).ravel())) / max(
            float(np.linalg.norm(expected_cv_pv.ravel())), 1e-30
        )
        gate("R22_subsegments_close_each_CV_pore_volume", cv_pv_rel <= 1e-10, cv_pv_rel)

        # ------------------------------------------------------------------------------------------
        # Freeze R29 candidate-execution protocol.
        # ------------------------------------------------------------------------------------------
        stage = "R29_candidate_execution_protocol_freeze"

        protocol = {
            "milestone": M,
            "status": PASS,
            "accepted_parent": {
                "canonical_day": DAY,
                "state_sha256": R25R3_STATE_SHA256,
                "flow_geometry_sha256": R22_EPOCH_SHA256,
                "pressure_epoch_sha256": PRESSURE_EPOCH_SHA256,
                "cartesian_component_mass_is_primary": True,
            },
            "candidate_time_step": {
                "rule": "E37A physics-derived 200-CV CFL step on frozen R22 geometry",
                "xi_face_count": NCV + 1,
                "dxi": dxi,
                "CFL": float(sg7a.CFL),
                "max_abs_df_dS": max_df,
                "max_dimensionless_wave_speed": max_wave_speed,
                "fastest_tau_end_days": fastest_tau_days,
                "nominal_dt_days": nominal_dt_days,
                "candidate_target_day": DAY + nominal_dt_days,
                "physical_time_commit_in_R29": False,
            },
            "CV_transport": {
                "implementation": "E37A.advance_component_mass_control_volumes",
                "conserved_variable": "CO2 component mass",
                "old_CV_mass": "accepted R25-R3 transport_CV_component_mass_kg",
                "old_CV_saturation": "accepted R25-R3 transport_CV_saturation",
                "injector_boundary_mass_rate_kg_day": INJECTOR_MASS_RATE_KG_DAY,
                "only_external_injection_source": "CV inlet face mass flux",
                "producer_sink": "CV outlet face component-mass flux grouped by R22 producer_labels",
                "global_identity": "sum(Delta_M_CV) = M_injected - M_produced",
            },
            "residual_well_coupling": {
                "injector_residual_mass_kg": injector_residual,
                "producer_residual_mass_kg": producer_residual,
                "active_well_residual_mass_kg": active_well_residual,
                "active_well_residual_fraction_of_total_residual": (
                    active_well_residual / total_residual if total_residual > 0.0 else 0.0
                ),
                "rule": (
                    "during the current frozen-flow epoch, external well component exchange "
                    "couples only through the accepted CV inlet/outlet mass fluxes; the deferred "
                    "Cartesian residual is not directly injected into or withdrawn from by wells"
                ),
                "physical_immobility_claim": False,
                "residual_direct_well_source_sink_execution": False,
                "residual_reconsidered_at_next_whole_cartesian_reprojection": True,
            },
            "delta_mapback": {
                "implementation": "E37A.map_control_volume_increment_to_grid subsegment mass-difference partition",
                "absolute_mapback_forbidden": True,
                "delta_only": True,
                "subsegment_identity": (
                    "Delta_M_sub = PV_sub * [rho(S_new,p_sub)*(S_new-Swc) "
                    "- rho(S_old,p_sub)*(S_old-Swc)]"
                ),
                "cell_deposition": "sum Delta_M_sub by SG7D flat_cell",
                "global_transfer_identity": "sum(Delta_M_grid) = sum(Delta_M_CV)",
                "parent_cartesian_identity": "M_grid_candidate = M_grid_parent + Delta_M_grid",
            },
            "residual_preservation": {
                "residual_grid_block_is_unchanged_during_R29_candidate": True,
                "represented_grid_candidate_identity": (
                    "M_represented_candidate = M_represented_parent + Delta_M_grid"
                ),
                "represented_grid_candidate_nonnegative_required": True,
                "candidate_split_identity": (
                    "M_grid_candidate = M_residual_parent + M_represented_candidate"
                ),
                "delta_may_not_consume_frozen_residual": True,
            },
            "well_mass_ledger": {
                "injected_mass": "500000 kg/day * dt_days",
                "produced_mass": "sum CV outlet component-mass flux * dt_days",
                "candidate_global_identity": (
                    "sum(M_grid_candidate)-sum(M_grid_parent) = M_injected - M_produced"
                ),
                "no_additional_source_local_mass_closure": True,
                "no_direct_residual_well_correction": True,
            },
            "precommit_gates": {
                "CV_mass_nonnegative": True,
                "CV_mass_to_saturation_inversion_PASS": True,
                "CV_saturation_bounds_0p20_to_0p80": True,
                "CV_global_source_sink_closure": True,
                "subsegment_to_CV_delta_closure": True,
                "represented_grid_candidate_nonnegative": True,
                "residual_sidecar_bytewise_or_valuewise_unchanged": True,
                "candidate_grid_mass_nonnegative": True,
                "candidate_grid_cell_pressure_capacity_not_exceeded": True,
                "candidate_global_source_sink_closure": True,
                "candidate_grid_mass_to_saturation_inversion_PASS": True,
            },
            "R29_failure_semantics": {
                "scientific_gate_failure": "immutable SCIENTIFIC FAIL; no automatic rerun",
                "technical_or_authority_failure": "immutable BLOCK",
                "automatic_dt_reduction_authorized": False,
                "support_growth_authorized": False,
                "residual_promotion_authorized": False,
                "mass_clipping_or_rescaling_authorized": False,
            },
            "R29_commit_semantics": {
                "candidate_state_may_be_published": True,
                "candidate_state_is_not_authoritative_until_acceptance_audit": True,
                "physical_time_advance_committed": False,
                "pressure_refresh_executed": False,
                "Darcy_Pollock_TOF_refresh_executed": False,
                "P3_authorized": False,
            },
        }

        classification = (
            "R6R28_FROZEN_FLOW_CV_COMPONENT_MASS_DELTA_MAPBACK_AND_DEFERRED_RESIDUAL_"
            "WELL_COUPLING_PROTOCOL_FROZEN_R29_PROVISIONAL_TRANSPORT_CANDIDATE_EXECUTION_NEXT"
        )

        summary = {
            "milestone": M,
            "name": NAME,
            "status": PASS,
            "classification": classification,
            "accepted_state_sha256": R25R3_STATE_SHA256,
            "injector_completion_count": 5,
            "producer_completion_count": 20,
            "injector_completion_residual_mass_kg": injector_residual,
            "producer_completion_residual_mass_kg": producer_residual,
            "active_well_completion_residual_mass_kg": active_well_residual,
            "total_residual_mass_kg": total_residual,
            "active_well_residual_fraction_of_total_residual": (
                active_well_residual / total_residual if total_residual > 0.0 else 0.0
            ),
            "injector_completion_total_component_mass_kg": injector_total,
            "producer_completion_total_component_mass_kg": producer_total,
            "nominal_dt_days": nominal_dt_days,
            "candidate_target_day": DAY + nominal_dt_days,
            "CV_pore_volume_relative_closure": cv_pv_rel,
            "residual_direct_well_exchange_frozen_out_for_current_epoch": True,
            "delta_mapback_required": True,
            "absolute_mapback_forbidden": True,
            "represented_grid_nonnegative_gate_required": True,
            "precommit_cell_capacity_gate_required": True,
            "physical_time_commit_authorized_now": False,
            "transport_execution_performed": False,
            "mapback_execution_performed": False,
            "P3_authorized": False,
        }

        decision = {
            "milestone": M,
            "status": PASS,
            "classification": classification,
            "P2_R6_R29_authorized": True,
            "P2_R6_R29_name": (
                "Controlled Post-Day375 Frozen-Flow Capacity-Limited Split-State "
                "Transport Candidate Execution — No Time Commit"
            ),
            "P2_R6_R29_execution_authorized": True,
            "P2_R6_R29_candidate_only": True,
            "P2_R6_R29_must_bind_R28_protocol": True,
            "P2_R6_R29_must_bind_R26_acceptance": True,
            "P2_R6_R29_must_bind_R25R3_state_SHA": True,
            "P2_R6_R29_R25R3_state_sha256": R25R3_STATE_SHA256,
            "P2_R6_R29_dt_days": nominal_dt_days,
            "P2_R6_R29_candidate_target_day": DAY + nominal_dt_days,
            "residual_direct_well_exchange_authorized": False,
            "CV_boundary_well_flux_is_only_external_exchange": True,
            "absolute_mapback_authorized": False,
            "CV_delta_mapback_authorized": True,
            "residual_sidecar_mutation_authorized": False,
            "automatic_dt_reduction_authorized": False,
            "support_growth_authorized": False,
            "physical_time_advance_authorized": False,
            "pressure_refresh_authorized": False,
            "P3_authorized": False,
            "P4_authorized": False,
            "P5_training_authorized": False,
        }

        # ------------------------------------------------------------------------------------------
        # Publish design artifacts only.
        # ------------------------------------------------------------------------------------------
        stage = "design_publication"

        out.mkdir(parents=True, exist_ok=False)
        (out / f"PAD_Stream_{OUT_TOKEN}_Summary.json").write_bytes(jb(summary))
        (out / f"{OUT_TOKEN}_FrozenFlow_Transport_DeltaMapback_Protocol.json").write_bytes(jb(protocol))
        (out / f"{OUT_TOKEN}_Residual_Well_Overlap_Audit.csv").write_bytes(csvb(rows))
        (out / f"{OUT_TOKEN}_Decision_Contract.json").write_bytes(jb(decision))
        (out / f"{OUT_TOKEN}_Final_Gate_Matrix.csv").write_bytes(csvb(gates))

        manifest_rows = []
        for p in sorted(out.iterdir()):
            if p.is_file():
                manifest_rows.append({
                    "file": p.name,
                    "sha256": sha(p),
                    "bytes": p.stat().st_size,
                })
        (out / f"{OUT_TOKEN}_Artifact_Manifest.csv").write_bytes(csvb(manifest_rows))

        print("=" * 190)
        print(M, "PASS")
        print("Classification                              :", classification)
        print("Accepted state SHA256                       :", R25R3_STATE_SHA256)
        print("Injector residual at completions kg         :", injector_residual)
        print("Producer residual at completions kg         :", producer_residual)
        print("Active-well residual / total residual       :", active_well_residual, "/", total_residual)
        print("Nominal candidate dt days                   :", nominal_dt_days)
        print("Candidate target day                        :", DAY + nominal_dt_days)
        print("CV pore-volume relative closure             :", cv_pv_rel)
        print("Residual direct well exchange               : False")
        print("Delta mapback / absolute mapback            : Required / Forbidden")
        print("Residual sidecar mutation in R29            : False")
        print("Physical time commit in R29                 : False")
        print("R29 candidate execution authorized          : True")
        print("P3 authorized                               : False")
        print("=" * 190)
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
                "R27_design_preserved": True,
                "R26_acceptance_preserved": True,
                "R25R3_state_preserved": True,
                "state_mutation_executed": False,
                "transport_execution_executed": False,
                "mapback_executed": False,
                "physical_time_advance_executed": False,
                "P3_authorized": False,
                "automatic_rerun_authorized": False,
                "gates_completed": gates,
            }))
        print("=" * 190)
        print(M, "TECHNICAL / AUTHORITY BLOCK")
        print("Stage    :", stage)
        print("Exception:", repr(exc))
        print("NO TRANSPORT / MAPBACK / TIME ADVANCE.")
        print("=" * 190)
        return 2


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", type=Path, default=Path("."))
    ap.add_argument(
        "--drive-root",
        type=Path,
        default=Path("/content/drive/MyDrive/PAD_Stream_Compute"),
    )
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        selftest()
        raise SystemExit(0)

    raise SystemExit(main(args.project_root, args.drive_root))
