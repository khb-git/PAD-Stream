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


MILESTONE = "POSTV16-AV4-F3"
PROTOCOL_ID = (
    "POSTV16_AV4_F3_SPLIT_STATE_RESTART_MODEL_SIGNATURE_AND_"
    "PHYSICS_TEACHER_PROTOCOL_FREEZE_V1"
)

STATUS_PASS = (
    "AV4F3_F2R3_ACCEPTED_SPLIT_STATE_BOUND_RESTARTABLE_200CV_17CHANNEL_"
    "MODEL_SIGNATURE_TEMPORAL_SEMANTICS_CONSERVATIVE_TEACHER_LOOP_AND_"
    "TRAIN_VALIDATION_OOD_FIREWALLS_PROSPECTIVELY_FROZEN_NO_TEACHER_EXECUTION"
)
STATUS_BLOCKED = "AV4F3_PROTOCOL_FREEZE_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT_F2R3_COMMIT = "8e339905f1a9a03521d999733e4f6146e84475d0"

GRID = (15, 50, 50)
NSL = 1078
NN = 201
NCV = 200

PARENT_DAY = 365.0
TARGET_DAY = 500.0
DELTA_DAY = 135.0

SWC = 0.20
SOR = 0.20
SPAN = 0.60

HIDDEN_UNITS = 64
LSTM_LAYERS = 2
INPUT_CHANNELS = 17
MODEL_PARAMETERS = 54081

TRAINING_SEED = 16021
BATCH_SIZE = 64
MAX_EPOCHS = 300
INITIAL_LR = 1.0e-3
EARLY_STOP_PATIENCE = 30
EARLY_STOP_MIN_DELTA = 1.0e-6
LR_FACTOR = 0.5
LR_PATIENCE = 10
MIN_LR = 1.0e-6
LAMBDA_DATA = 1.0
LAMBDA_PHYS = 0.01
R0 = 1.0

CANONICAL_DAYS = [30.0, 60.0, 100.0, 150.0, 250.0, 365.0, 500.0, 750.0, 1000.0]
ADJACENT_RESTART_PAIRS = [
    [30.0, 60.0],
    [60.0, 100.0],
    [100.0, 150.0],
    [150.0, 250.0],
    [250.0, 365.0],
    [365.0, 500.0],
    [500.0, 750.0],
    [750.0, 1000.0],
]

REALIZATION_SPLIT = {
    "TRAIN": ["AV3CR0001", "AV3CR0002"],
    "VALIDATION": ["AV3CR0003"],
    "LOCKED_OOD_TEST": ["AV3CR0004"],
}

FLOW15 = [
    "xi_cv",
    "pollock_tau_hat_cv",
    "adv_tau_hat_cv",
    "log10_Kh_cv",
    "log10_Kz_over_Kh_cv",
    "porosity_cv",
    "pressure_z_cv",
    "parent_time_hat",
    "target_time_hat",
    "delta_time_hat",
    "delta_eta_streamline",
    "nw_hat_cv",
    "no_hat_cv",
    "krw_max_hat_cv",
    "kro_max_hat_cv",
]

STATE2 = [
    "parent_CV_saturation_hat",
    "parent_CV_mass_fraction",
]

CHANNELS17 = FLOW15 + STATE2

# --------------------------------------------------------------------------------------------------
# Exact repository source authorities.
# --------------------------------------------------------------------------------------------------

F2R3 = "PAD_Stream_POSTV16_AV4_F2_R3_Bounded_Physical_Occupancy_Projection_Execution.py"
F2R3_BLOB = "359f3c0edf87e10bb4006cacdd271cd426fed22b"

E1R2 = (
    "PAD_Stream_POSTV16_AV4_A3_E1_R2_Fully_Schema_Corrected_"
    "Refreshed_X13_Structural_InputDomain_Audit.py"
)
E1R2_BLOB = "058f00fd12bd491dc7d7d7e471af3d4ff865af70"

AV3A3 = "PAD_Stream_POSTV16_AV3_A3_Transport_Teacher_Residual_and_PIRNN_Protocol_Freeze.py"
AV3A3_BLOB = "40fe89c142e62aad750a749f0a8ae452574f28bd"

AV3A3R1 = (
    "PAD_Stream_POSTV16_AV3_A3_R1_"
    "First9_CellCentered_Geometry_and_Normalization_Authority_Correction.py"
)
AV3A3R1_BLOB = "2a70ef6b67ddefee61b5a9ab2fb080755fdb4b49"

AV3A4R2 = (
    "PAD_Stream_POSTV16_AV3_A4_R2_"
    "Corrected_Certification_Teacher_Dataset_and_LockedOOD_Predictor.py"
)
AV3A4R2_BLOB = "289901331e835afb44ff2f665fe9a6bbea2eac19"

AV3A5R2 = "PAD_Stream_POSTV16_AV3_A5_R2_Frozen_Checkpoint_OneTouch_OOD_Continuation.py"
AV3A5R2_BLOB = "b2dd3fb27966a51e6a6057e444dfdb617976b36f"

A2E = "PAD_Stream_POSTV16_AV4_A2_E_Controlled_Day365_Dynamic_Flow_Refresh_Execution.py"
A2E_BLOB = "79a8969233b72b4543edd382a0c3d1028c6dca09"

E37A = "PAD_Stream_V16E37A_Control_Volume_Aligned_Conservative_Streamline_Grid_Transfer.py"
E37A_BLOB = "0bbf98ed89cee9128ef1d313c321f9a401b4e9f0"

SOURCE_BLOBS = {
    F2R3: F2R3_BLOB,
    E1R2: E1R2_BLOB,
    AV3A3: AV3A3_BLOB,
    AV3A3R1: AV3A3R1_BLOB,
    AV3A4R2: AV3A4R2_BLOB,
    AV3A5R2: AV3A5R2_BLOB,
    A2E: A2E_BLOB,
    E37A: E37A_BLOB,
}

# --------------------------------------------------------------------------------------------------
# Formal Drive authorities.
# --------------------------------------------------------------------------------------------------

BASE_AV4 = Path("post_v16") / RID / "POSTV16_AV4_Dynamic_Flow_Coupling"

F2R3_REL = BASE_AV4 / "POSTV16_AV4_F2_R3_Bounded_Physical_Occupancy_Projection_Execution"
F2R3_SUMMARY = "PAD_Stream_POSTV16_AV4_F2_R3_Summary.json"
F2R3_STATE = "POSTV16_AV4_F2_R3_Accepted_Parent_Restart_State.npz"
F2R3_PROJECTION = "POSTV16_AV4_F2_R3_Projection_Closure_Audit.json"
F2R3_CAPACITY = "POSTV16_AV4_F2_R3_CV_Capacity_and_Inversion_Audit.json"
F2R3_HANDOFF = "POSTV16_AV4_F2_R3_F3_Handoff_Contract.json"
F2R3_DECISION = "POSTV16_AV4_F2_R3_Decision_Contract.json"
F2R3_MANIFEST = "POSTV16_AV4_F2_R3_Artifact_Manifest.csv"
F2R3_STATUS = (
    "AV4F2R3_BOUNDED_PHYSICAL_OCCUPANCY_SPLIT_STATE_PARENT_PROJECTION_"
    "EXECUTION_PASS_CAPACITY_FEASIBLE_E37A_INVERSION_PASS_NO_TIME_ADVANCE"
)

OUT_REL = BASE_AV4 / "POSTV16_AV4_F3_Split_State_Restart_Model_and_Teacher_Protocol_Freeze"
BLOCK_REL = BASE_AV4 / "POSTV16_AV4_F3_BLOCKED"


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


def model_parameter_count(input_channels: int, units: int) -> int:
    first = 4 * units * (units + input_channels + 1)
    second = 4 * units * (units + units + 1)
    dense = units + 1
    return first + second + dense


def self_test() -> None:
    assert len(FLOW15) == 15
    assert len(STATE2) == 2
    assert len(CHANNELS17) == INPUT_CHANNELS == 17
    assert len(set(CHANNELS17)) == 17
    assert NCV == NN - 1
    assert PARENT_DAY + DELTA_DAY == TARGET_DAY
    assert model_parameter_count(INPUT_CHANNELS, HIDDEN_UNITS) == MODEL_PARAMETERS
    assert len(ADJACENT_RESTART_PAIRS) == 8
    assert ADJACENT_RESTART_PAIRS[5] == [365.0, 500.0]
    assert "target_eta_sequence" not in CHANNELS17
    assert "delta_eta_streamline" in CHANNELS17
    assert "parent_CV_mass_fraction" in CHANNELS17
    print(
        "POSTV16-AV4-F3 split-state restart model / teacher "
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
        "POSTV16-AV4-F3 — SPLIT-STATE RESTART MODEL-SIGNATURE + "
        "PHYSICS-TEACHER PROTOCOL FREEZE"
    )
    print("=" * 214)
    print("DESIGN / FREEZE ONLY.")
    print("NO TEACHER EXECUTION. NO MODEL BUILD/TRAINING. NO CHECKPOINT LOAD/INFERENCE.")
    print("NO PHYSICAL-TIME ADVANCE. NO FUTURE MAPBACK. NO OOD OPENING. NO CMG.")
    print("THE F2-R3 CARTESIAN RESIDUAL REMAINS AN EXACT NON-NEURAL SIDECAR.")
    print()

    try:
        # ------------------------------------------------------------------------------------------
        # Repository and source authority.
        # ------------------------------------------------------------------------------------------
        stage = "repository_authority"

        parent = git_text(root, "rev-parse", "HEAD^")
        status = git_text(root, "status", "--porcelain")

        gate(
            "repository_parent_is_F2R3_commit",
            parent == PARENT_F2R3_COMMIT,
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

        # Explicitly bind the historical restart incompatibility at source level.
        e1_source = (root / E1R2).read_text(encoding="utf-8", errors="replace")
        gate(
            "E1R2_historical_parent_state_channel_count_zero_bound",
            '"historical_parent_state_input_channel_count": len(parent_state_channels)'
            in e1_source
            and '"direct_day365_to_day500_checkpoint_restart_authority": False'
            in e1_source
            and '"delta_time_135d_substitution_authorized": False'
            in e1_source,
        )

        # ------------------------------------------------------------------------------------------
        # Bind formal F2-R3 accepted split state.
        # ------------------------------------------------------------------------------------------
        stage = "F2R3_accepted_state_binding"

        f2 = drive / F2R3_REL
        gate("F2R3_output_present", f2.is_dir(), str(f2))
        mf2 = verify_manifest(f2, F2R3_MANIFEST)
        gate("F2R3_manifest_exact_9", len(mf2) == 9, len(mf2))
        gate("F2R3_state_manifested", F2R3_STATE in mf2, F2R3_STATE)

        sf2 = load_json(f2 / F2R3_SUMMARY)
        pf2 = load_json(f2 / F2R3_PROJECTION)
        cf2 = load_json(f2 / F2R3_CAPACITY)
        hf2 = load_json(f2 / F2R3_HANDOFF)
        df2 = load_json(f2 / F2R3_DECISION)

        gate("F2R3_status_exact", sf2["status"] == F2R3_STATUS, sf2["status"])
        gate(
            "F2R3_accepted_split_state_exact",
            sf2["accepted_split_state"] is True
            and sf2["overloaded_CV_count"] == 0
            and sf2["projection_execution"] is True
            and sf2["CV_mass_inversion_execution"] is True
            and abs(float(sf2["global_ledger_residual_kg"])) <= 1.0e-12,
        )
        gate(
            "F2R3_mass_partition_nontrivial",
            0.0 < float(sf2["mapped_fraction_of_parent_mass"]) < 1.0
            and 0.0 < float(sf2["residual_fraction_of_parent_mass"]) < 1.0
            and float(sf2["residual_inside_S0_kg"]) > 0.0,
            {
                "mapped_fraction": sf2["mapped_fraction_of_parent_mass"],
                "residual_fraction": sf2["residual_fraction_of_parent_mass"],
                "residual_inside_S0_kg": sf2["residual_inside_S0_kg"],
            },
        )
        gate(
            "F2R3_capacity_and_inversion_PASS",
            cf2["capacity_PASS"] is True
            and cf2["CV_mass_inversion_PASS"] is True
            and int(cf2["overloaded_CV_count"]) == 0
            and float(cf2["CV_saturation_min"]) >= SWC
            and float(cf2["CV_saturation_max"]) <= 1.0 - SOR,
        )
        gate(
            "F2R3_projection_semantics_exact",
            pf2["operator"]
            == "m_q = M_parent[c(q)] * PV_q / max(PV_cell_c, W_c)"
            and pf2["support_domain_changed"] is False
            and pf2["reverse_halo_pullback_performed"] is False
            and pf2["LP_or_repair_search_performed"] is False,
        )
        gate(
            "F2R3_F3_handoff_exact",
            hf2["milestone"] == MILESTONE
            and hf2["authorized"] is True
            and hf2["execution"] is True
            and float(hf2["accepted_parent_day"]) == PARENT_DAY
            and float(hf2["first_candidate_target_day"]) == TARGET_DAY
            and float(hf2["first_candidate_delta_day"]) == DELTA_DAY,
            hf2,
        )
        gate(
            "F2R3_downstream_firewalls_before_F3",
            hf2["teacher_execution_authorized_in_F3"] is False
            and hf2["model_training_authorized_in_F3"] is False
            and hf2["checkpoint_inference_authorized_in_F3"] is False
            and hf2["physical_time_advance_authorized_in_F3"] is False
            and df2["teacher_execution_authorized"] is False
            and df2["A3_E2_authorized"] is False
            and df2["AV4_dynamic_transport_execution_authorized"] is False,
        )

        # ------------------------------------------------------------------------------------------
        # Verify accepted state artifact schema without performing physics.
        # ------------------------------------------------------------------------------------------
        stage = "accepted_state_schema_binding"

        import numpy as np

        with np.load(f2 / F2R3_STATE, allow_pickle=False) as z:
            state_keys = set(z.files)
            cv_mass_shape = z["parent_CV_component_mass_kg"].shape
            cv_sat_shape = z["parent_CV_saturation"].shape
            cv_cap_shape = z["parent_CV_capacity_kg"].shape
            residual_shape = z["residual_grid_component_mass_kg"].shape
            alpha_shape = z["occupancy_fraction_alpha"].shape

        required_state = {
            "parent_CV_component_mass_kg",
            "parent_CV_saturation",
            "parent_CV_capacity_kg",
            "parent_CV_pore_volume_m3",
            "parent_CV_pressure_mass_coeff",
            "residual_grid_component_mass_kg",
            "occupancy_fraction_alpha",
            "SG7D_occupancy_pore_volume_Wc_m3",
            "physical_cell_pore_volume_m3",
            "mapped_grid_component_mass_kg",
            "subsegment_parent_mass_kg",
            "subsegment_flat_cell",
            "subsegment_streamline",
            "subsegment_control_volume",
            "subsegment_pore_volume_m3",
            "parent_total_mass_kg",
            "mapped_CV_mass_kg",
            "residual_grid_mass_kg",
            "parent_day",
        }
        gate(
            "F2R3_required_restart_state_arrays_present",
            required_state.issubset(state_keys),
            sorted(required_state),
        )
        gate(
            "F2R3_restart_state_shapes_exact",
            cv_mass_shape == (NSL, NCV)
            and cv_sat_shape == (NSL, NCV)
            and cv_cap_shape == (NSL, NCV)
            and residual_shape == GRID
            and alpha_shape == GRID,
            {
                "CV_mass": cv_mass_shape,
                "CV_sat": cv_sat_shape,
                "CV_capacity": cv_cap_shape,
                "residual": residual_shape,
                "alpha": alpha_shape,
            },
        )

        # ------------------------------------------------------------------------------------------
        # Freeze exact 200-CV / 17-channel restart model signature.
        # ------------------------------------------------------------------------------------------
        stage = "restart_model_signature_freeze"

        model = {
            "milestone": MILESTONE,
            "architecture_family": (
                "state_conditioned_stacked_LSTM_TimeDistributed_Dense_"
                "bounded_future_CV_mass_fraction"
            ),
            "sequence_length": NCV,
            "input_channels": INPUT_CHANNELS,
            "channel_order": CHANNELS17,
            "flow_conditioning_channels": FLOW15,
            "explicit_parent_state_channels": STATE2,
            "node_to_CV_reduction": {
                "source_nodes": NN,
                "target_control_volumes": NCV,
                "rule_for_continuous_nodal_fields": (
                    "CV_j = 0.5*(node_j + node_{j+1}) for j=0..199"
                ),
                "applies_to": [
                    "xi",
                    "pollock_tau_hat",
                    "adv_tau_hat",
                    "log10_Kh",
                    "log10_Kz_over_Kh",
                    "porosity",
                    "pressure_z",
                    "nw_hat",
                    "no_hat",
                    "krw_max_hat",
                    "kro_max_hat",
                ],
                "no_node_to_CV_mass_projection_reperformed": True,
                "parent_CV_state_authority": "F2-R3 accepted CV arrays",
            },
            "state_channel_scaling": {
                "parent_CV_saturation_hat": (
                    "(parent_CV_saturation - 0.20) / 0.60"
                ),
                "parent_CV_mass_fraction": (
                    "parent_CV_component_mass_kg / parent_CV_capacity_kg"
                ),
                "mass_fraction_bounds": [0.0, 1.0],
            },
            "temporal_channels": {
                "parent_time_hat": "t_parent_days / 1000",
                "target_time_hat": "t_target_days / 1000",
                "delta_time_hat": "(t_target_days - t_parent_days) / 1000",
                "delta_eta_streamline": (
                    "(t_target_days-t_parent_days)*86400 / parent_epoch_tau_end_s; "
                    "broadcast across the 200 CVs of one streamline"
                ),
                "historical_absolute_target_eta_sequence_reused": False,
            },
            "output": {
                "name": "future_CV_mass_fraction",
                "shape_per_streamline": [NCV, 1],
                "activation": "sigmoid",
                "bounds": [0.0, 1.0],
                "physical_reconstruction": (
                    "future_CV_component_mass_kg = future_CV_mass_fraction * "
                    "parent_epoch_CV_capacity_kg"
                ),
                "future_CV_saturation": (
                    "derived by frozen E37A mass-to-saturation inversion under "
                    "the parent-epoch CV pressure-mass coefficients before mapback"
                ),
            },
            "LSTM_layers": LSTM_LAYERS,
            "hidden_units": HIDDEN_UNITS,
            "TimeDistributed_output_units": 1,
            "parameter_count": MODEL_PARAMETERS,
            "parameter_count_formula": (
                "4*64*(64+17+1) + 4*64*(64+64+1) + (64+1)"
            ),
            "historical_AV3_checkpoint_direct_weight_compatibility": False,
            "historical_AV3_checkpoint_role": (
                "immutable absolute-time baseline only; no production restart reuse"
            ),
            "residual_grid_direct_neural_input": False,
            "residual_grid_role": (
                "exact recurrent non-neural sidecar that remains in the authoritative "
                "Cartesian parent mass and re-enters through conservative mapback + "
                "target-epoch flow refresh"
            ),
        }

        gate("restart_signature_17_channels", len(CHANNELS17) == 17, CHANNELS17)
        gate(
            "restart_signature_has_explicit_parent_state",
            STATE2
            == [
                "parent_CV_saturation_hat",
                "parent_CV_mass_fraction",
            ],
            STATE2,
        )
        gate(
            "restart_signature_parameter_count_exact",
            model_parameter_count(INPUT_CHANNELS, HIDDEN_UNITS)
            == MODEL_PARAMETERS,
            MODEL_PARAMETERS,
        )
        gate(
            "restart_signature_no_historical_absolute_eta_channel",
            "target_eta_sequence" not in CHANNELS17
            and "delta_eta_streamline" in CHANNELS17,
        )

        # ------------------------------------------------------------------------------------------
        # Freeze restart temporal semantics.
        # ------------------------------------------------------------------------------------------
        stage = "restart_temporal_semantics_freeze"

        temporal = {
            "milestone": MILESTONE,
            "first_controlled_transition": {
                "realization": "AV3CR0003",
                "paired_porosity": "AV2PHI0003",
                "partition": "VALIDATION",
                "parent_day": PARENT_DAY,
                "target_day": TARGET_DAY,
                "delta_day": DELTA_DAY,
                "parent_time_hat": PARENT_DAY / 1000.0,
                "target_time_hat": TARGET_DAY / 1000.0,
                "delta_time_hat": DELTA_DAY / 1000.0,
            },
            "restart_pair_rule": (
                "teacher/model samples are ordered adjacent parent->target pairs; "
                "the parent state is an explicit input and delta time is not substituted "
                "for absolute target time"
            ),
            "canonical_days": CANONICAL_DAYS,
            "adjacent_restart_pairs": ADJACENT_RESTART_PAIRS,
            "pair_count_per_realization": len(ADJACENT_RESTART_PAIRS),
            "historical_absolute_trajectory_semantics_rejected_for_restart": True,
            "delta135_as_drop_in_replacement_for_historical_target_time": False,
            "absolute500_without_parent_state_as_restart": False,
        }

        # ------------------------------------------------------------------------------------------
        # Freeze split-state teacher / recurrent physics loop.
        # ------------------------------------------------------------------------------------------
        stage = "split_state_teacher_protocol_freeze"

        teacher = {
            "milestone": MILESTONE,
            "execution_in_F3": False,
            "first_controlled_teacher": (
                "AV3CR0003 / AV2PHI0003 Day365->Day500"
            ),
            "parent_authorities": [
                "F2-R3 accepted 1078x200 CV component mass",
                "F2-R3 accepted 1078x200 CV saturation",
                "F2-R3 exact 15x50x50 residual grid component mass",
                "A2-E parent-epoch refreshed pressure/flux/Pollock/TOF geometry",
            ],
            "transport_substep_geometry": (
                "hold the parent-epoch refreshed flow/streamline geometry fixed "
                "during one restart transport interval"
            ),
            "restart_teacher_state": (
                "initialize the 200-CV transport teacher from F2-R3 parent CV state, "
                "not from the historical common initial saturation"
            ),
            "physics_lineage_to_preserve": {
                "fractional_flow_and_spatial_Corey": (
                    "AV3-A3/A4-R2 source-authentic local nw/no/krw_max/kro_max physics"
                ),
                "advection": (
                    "positive-flow conservative upwind finite-volume transport"
                ),
                "capillarity": (
                    "same AV3 source-authentic capillary constitutive physics, "
                    "re-derived on 200 CV geometry and independently certified in F4"
                ),
                "fixed_constants": {
                    "Swc": SWC,
                    "Sor": SOR,
                    "mu_w_cp": 0.5,
                    "mu_o_cp": 5.0,
                    "Pe_c": 22.0,
                    "lambda_c": 2.0,
                },
            },
            "residual_grid_participation": {
                "neural_prediction": False,
                "zeroed_or_discarded": False,
                "separate_transport_along_nonexistent_streamlines": False,
                "role_during_parent_geometry_substep": (
                    "remain inside the exact authoritative parent Cartesian mass; "
                    "the neural/teacher operator predicts only the represented CV-state change"
                ),
                "conservative_future_grid_update": (
                    "Delta_M_CV = M_CV_future - M_CV_parent; apply frozen E37A "
                    "control-volume increment mapback to the exact full parent grid "
                    "component mass (which already contains the residual sidecar)"
                ),
                "target_epoch_refresh": (
                    "invert future grid component mass to saturation, execute the "
                    "same-time mobility/pressure/Darcy/Pollock/TOF refresh at t_target, "
                    "then reapply the accepted bounded physical-occupancy projection "
                    "to obtain the next split recurrent state"
                ),
            },
            "required_mass_ledger": [
                "parent full grid mass = mapped parent CV state + residual sidecar",
                "future full grid mass = exact parent full grid mass + conservative mapback(Delta_M_CV)",
                "target refreshed split state must close exactly to future full grid mass",
            ],
            "teacher_targets": {
                "primary_supervised_target": (
                    "future_CV_mass_fraction on the parent-epoch CV geometry"
                ),
                "derived_target": "future_CV_saturation by E37A inversion",
                "recurrent_handoff_target": (
                    "target-epoch refreshed and bounded-reprojected split state"
                ),
            },
            "teacher_certification_required_before_dataset_generation": [
                "finite bounded CV state",
                "CV capacity feasibility",
                "CV mass-to-saturation inversion closure",
                "conservative E37A increment mapback closure",
                "future grid mass nonnegative and saturation within physical bounds",
                "target-epoch same-time flow refresh PASS",
                "target bounded split-state projection PASS",
                "global parent->future component-mass accounting",
            ],
            "forbidden_in_teacher_protocol": [
                "use historical AV3 checkpoint as restart teacher",
                "hold residual mass outside the global parent ledger",
                "reverse H1->S0 pullback",
                "support expansion after observing teacher outcome",
                "clipping/discarding component mass",
                "CMG guidance during AV4 teacher development",
            ],
        }

        # ------------------------------------------------------------------------------------------
        # Freeze objective / split / normalization / OOD firewalls.
        # ------------------------------------------------------------------------------------------
        stage = "training_validation_OOD_firewall_freeze"

        training = {
            "milestone": MILESTONE,
            "execution_in_F3": False,
            "realization_split": REALIZATION_SPLIT,
            "restart_pairs": ADJACENT_RESTART_PAIRS,
            "profiles_per_pair_per_realization": NSL,
            "TRAIN_restart_profiles": 2 * len(ADJACENT_RESTART_PAIRS) * NSL,
            "VALIDATION_restart_profiles": len(ADJACENT_RESTART_PAIRS) * NSL,
            "LOCKED_OOD_restart_profiles": len(ADJACENT_RESTART_PAIRS) * NSL,
            "first_controlled_teacher_pair_is_validation_only": True,
            "normalization": {
                "fit_statistics_on_restart_TRAIN_only": True,
                "validation_statistics_used_for_fit": False,
                "locked_OOD_statistics_used_for_fit": False,
                "fixed_analytical_scalings_preserved": {
                    "parent_CV_saturation_hat": "(S-0.20)/0.60",
                    "parent_CV_mass_fraction": "M/C",
                    "nw_hat": "(nw-3.0)/1.0",
                    "no_hat": "(no-3.0)/1.0",
                    "krw_max_hat": "(krw_max-0.80)/0.20",
                    "kro_max_hat": "(kro_max-0.80)/0.20",
                    "parent_time_hat": "t_parent_days/1000",
                    "target_time_hat": "t_target_days/1000",
                    "delta_time_hat": "delta_days/1000",
                },
                "restart_dynamic_pressure_and_any_new_fitted_scalars": (
                    "fit on restart TRAIN predictor features only after F4 teacher/signature "
                    "certification and before validation evaluation"
                ),
            },
            "objective_lineage": {
                "formula": "L_data + 0.01*L_phys",
                "lambda_data": LAMBDA_DATA,
                "lambda_phys": LAMBDA_PHYS,
                "R0": R0,
                "L_data": (
                    "MSE on future_CV_mass_fraction over 200 control volumes"
                ),
                "L_phys": (
                    "source-authentic conservative 200-CV restart transport residual; "
                    "F4 must construct and certify its algebra before any training"
                ),
                "objective_not_executed_in_F3": True,
            },
            "optimizer_baseline": {
                "name": "Adam",
                "learning_rate": INITIAL_LR,
                "batch_size": BATCH_SIZE,
                "max_epochs": MAX_EPOCHS,
                "random_seed": TRAINING_SEED,
                "early_stop_patience": EARLY_STOP_PATIENCE,
                "early_stop_min_delta": EARLY_STOP_MIN_DELTA,
                "lr_factor": LR_FACTOR,
                "lr_patience": LR_PATIENCE,
                "min_lr": MIN_LR,
                "hyperparameter_search_authorized_now": False,
            },
            "checkpoint_and_OOD": {
                "checkpoint_selection": "minimum validation total objective",
                "checkpoint_frozen_before_locked_OOD_teacher_generation": True,
                "LOCKED_OOD_realization": "AV3CR0004",
                "OOD_predictor_feature_access_before_checkpoint": True,
                "OOD_teacher_target_access_before_checkpoint": False,
                "OOD_metric_access_before_checkpoint": False,
                "post_checkpoint_OOD": (
                    "one locked-OOD teacher generation + one evaluation only"
                ),
                "no_OOD_retraining": True,
                "no_OOD_checkpoint_reselection": True,
                "no_OOD_normalization_refit": True,
                "no_OOD_hyperparameter_retuning": True,
                "no_second_OOD_evaluation": True,
            },
        }

        gate(
            "restart_profile_counts_exact",
            training["TRAIN_restart_profiles"] == 17248
            and training["VALIDATION_restart_profiles"] == 8624
            and training["LOCKED_OOD_restart_profiles"] == 8624,
            {
                "TRAIN": training["TRAIN_restart_profiles"],
                "VALIDATION": training["VALIDATION_restart_profiles"],
                "OOD": training["LOCKED_OOD_restart_profiles"],
            },
        )

        # ------------------------------------------------------------------------------------------
        # Freeze F4 controlled teacher/signature certification handoff.
        # ------------------------------------------------------------------------------------------
        stage = "F4_handoff_freeze"

        handoff = {
            "milestone": "POSTV16-AV4-F4",
            "name": (
                "Controlled Day365->Day500 Restart Teacher Construction + "
                "17-Channel Signature / Conservative Loop Certification"
            ),
            "authorized": True,
            "execution": True,
            "control_realization": "AV3CR0003",
            "paired_porosity": "AV2PHI0003",
            "partition": "VALIDATION",
            "parent_day": PARENT_DAY,
            "target_day": TARGET_DAY,
            "delta_day": DELTA_DAY,
            "allowed": [
                "construct the frozen 200-CV restart teacher on parent Day365 geometry",
                "construct the exact 17-channel CV-centered predictor tensor",
                "construct the untrained 2xLSTM64 bounded-output model and verify 54081 parameters",
                "execute the physics teacher for the single Day365->Day500 control transition",
                "certify the 200-CV conservative residual algebra",
                "execute E37A conservative Delta-CV mapback onto the exact full parent grid mass",
                "execute target-Day500 same-time flow refresh",
                "execute target bounded split-state reprojection",
                "publish teacher/signature/conservation certification artifacts",
            ],
            "forbidden": [
                "model training",
                "checkpoint creation or selection",
                "historical AV3 checkpoint restart inference",
                "locked OOD teacher generation or metrics",
                "normalization fit using validation or OOD",
                "hyperparameter search",
                "A3-E2",
                "general AV4 dynamic deployment",
                "CMG",
            ],
            "F5_dataset_generation_authorized": False,
            "model_training_authorized": False,
            "checkpoint_inference_authorized": False,
            "A3_E2_authorized": False,
            "AV4_dynamic_transport_execution_authorized": False,
        }

        decision = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "F2R3_split_state_bound": True,
            "historical_AV3_structural_restart_incompatibility_bound": True,
            "restart_model_signature_frozen": True,
            "restart_sequence_length": NCV,
            "restart_input_channels": INPUT_CHANNELS,
            "restart_model_parameters": MODEL_PARAMETERS,
            "explicit_parent_state_channels": STATE2,
            "residual_grid_direct_neural_input": False,
            "residual_grid_exact_sidecar_preserved": True,
            "restart_temporal_semantics_frozen": True,
            "teacher_loop_frozen": True,
            "TRAIN_VALIDATION_OOD_firewalls_frozen": True,
            "teacher_execution_performed": False,
            "model_built": False,
            "training_performed": False,
            "checkpoint_created": False,
            "checkpoint_model_loaded": False,
            "checkpoint_inference_performed": False,
            "physical_time_advanced": False,
            "future_mapback_performed": False,
            "locked_OOD_opened": False,
            "CMG_validation_performed": False,
            "F4_authorized": True,
            "F4_execution_authorized": True,
            "F5_dataset_generation_authorized": False,
            "A3_E2_authorized": False,
            "AV4_dynamic_transport_execution_authorized": False,
        }

        summary = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "protocol_id": PROTOCOL_ID,
            "accepted_parent_day": PARENT_DAY,
            "first_target_day": TARGET_DAY,
            "first_delta_day": DELTA_DAY,
            "sequence_length": NCV,
            "input_channels": INPUT_CHANNELS,
            "channel_order": CHANNELS17,
            "model_parameters": MODEL_PARAMETERS,
            "explicit_parent_state_channels": STATE2,
            "residual_grid_role": "exact_non_neural_recurrent_sidecar",
            "historical_target_eta_sequence_reused": False,
            "objective_lineage": "L_data + 0.01*L_phys",
            "TRAIN_restart_profiles": training["TRAIN_restart_profiles"],
            "VALIDATION_restart_profiles": training["VALIDATION_restart_profiles"],
            "LOCKED_OOD_restart_profiles": training["LOCKED_OOD_restart_profiles"],
            "teacher_execution": False,
            "model_training": False,
            "checkpoint_inference": False,
            "physical_time_advance": False,
            "F4_authorized": True,
            "F5_authorized": False,
            "A3_E2_authorized": False,
            "AV4_dynamic_transport_execution_authorized": False,
        }

        output_files = {
            "PAD_Stream_POSTV16_AV4_F3_Summary.json":
                json_bytes(summary),
            "POSTV16_AV4_F3_Restart_Model_Signature_Contract.json":
                json_bytes(model),
            "POSTV16_AV4_F3_Restart_Temporal_Semantics_Contract.json":
                json_bytes(temporal),
            "POSTV16_AV4_F3_Split_State_Physics_Teacher_Contract.json":
                json_bytes(teacher),
            "POSTV16_AV4_F3_Training_Validation_OOD_Firewall_Contract.json":
                json_bytes(training),
            "POSTV16_AV4_F3_F4_Handoff_Contract.json":
                json_bytes(handoff),
            "POSTV16_AV4_F3_Decision_Contract.json":
                json_bytes(decision),
            "POSTV16_AV4_F3_Final_Gate_Matrix.csv":
                csv_bytes(
                    [{"gate": name, **value} for name, value in gates.items()]
                ),
        }

        immutable_publish(out, output_files)

        manifest_rows = []
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name != "POSTV16_AV4_F3_Artifact_Manifest.csv":
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
                "POSTV16_AV4_F3_Artifact_Manifest.csv":
                    csv_bytes(manifest_rows)
            },
        )

        print()
        print("=" * 214)
        print(f"{MILESTONE}: SPLIT-STATE RESTART MODEL / TEACHER PROTOCOL FREEZE PASS")
        print("=" * 214)
        print("F2-R3 accepted split state                 : BOUND")
        print("Historical AV3 restart incompatibility     : BOUND")
        print("Restart sequence                           : 200 CVs")
        print("Restart input channels                     : 17")
        print("Explicit parent-state channels             : 2")
        print("Model                                       : 2 x LSTM64 -> TD Dense sigmoid")
        print("Parameter count                             :", MODEL_PARAMETERS)
        print("Residual grid direct neural input           : False")
        print("Residual grid exact recurrent sidecar       : True")
        print("First controlled transition                 : Day365 -> Day500")
        print("Teacher execution                           : False")
        print("Training / checkpoint inference             : False / False")
        print("Physical time advance                       : False")
        print("POSTV16-AV4-F4                              : AUTHORIZED")
        print("F5 dataset/training / A3-E2 / dynamic AV4   : NOT AUTHORIZED")
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
            "teacher_execution_performed": False,
            "model_built": False,
            "training_performed": False,
            "checkpoint_created": False,
            "checkpoint_model_loaded": False,
            "checkpoint_inference_performed": False,
            "physical_time_advanced": False,
            "future_mapback_performed": False,
            "locked_OOD_opened": False,
            "F4_authorized": False,
            "F5_dataset_generation_authorized": False,
            "A3_E2_authorized": False,
            "AV4_dynamic_transport_execution_authorized": False,
            "automatic_rerun_authorized": False,
        }

        data = json_bytes(report)
        p = blocked / "POSTV16_AV4_F3_Blocked_Report.json"
        if p.exists() and p.read_bytes() != data:
            p = blocked / (
                "POSTV16_AV4_F3_Blocked_Report_"
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
        print("NO TEACHER / TRAINING / RERUN AUTHORIZED.")
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
