#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import subprocess
from pathlib import Path
from typing import Any


MILESTONE = "POSTV16-AV2-A0"
STATUS_PASS = (
    "AV2A0_VARIABLE_POROSITY_SCIENTIFIC_SCOPE_AUTHORITY_GAP_AND_"
    "PHYSICS_IMPACT_PROSPECTIVELY_FROZEN_NO_EXECUTION"
)
STATUS_BLOCKED = "AV2A0_VARIABLE_POROSITY_SCOPE_FREEZE_BLOCKED"
PROTOCOL_ID = (
    "POSTV16_AV2_A0_VARIABLE_POROSITY_SCOPE_AND_AUTHORITY_GAP_FREEZE_V1"
)

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"

# Exact current main parent: AV1-E is frozen but its external-validation execution
# is deliberately deferred until the full AV1->AV5 framework is complete.
PARENT_AV1E_COMMIT = "b75bba125aa58c14d1372f653792408722921783"

R7R7E_FREEZE = (
    "PAD_Stream_POSTV16_AV1_D_R7_R7E_"
    "Scientific_PASS_Outcome_Freeze.py"
)
R7R7E_FREEZE_BLOB = "9b6c73e07622baa6e4d0f4d8e2b60710aabcae90"

AV1E = (
    "PAD_Stream_POSTV16_AV1_E_Prospective_External_Full_Physics_"
    "Deployment_Acceptance_Contract_Freeze.py"
)
AV1E_BLOB = "e5e685c7a7d9216e1ddd5fe84a17004d0ebfbee9"

R8R = "PAD_Stream_V16AR8R_Repaired_Foundation_Case_0001_Final_Assembly_Freeze.py"
R8R_BLOB = "00576330d14efd41ceeb81e2f38b14ba1ef01525"

SG5 = "PAD_Stream_V15SG5_Exact_Pollock_Streamlines.py"
SG5_BLOB = "9a0b64ea7e669904d0d9855ade1c6b052f05ecea"

C2 = "PAD_Stream_V16C2_Multi_Coordinate_Streamline_Transport_Database_Assembly.py"
C2_BLOB = "21ff44de456102772c99f7ddc80898c9139a76db"

C4 = "PAD_Stream_V16C4_Model_Ready_Conditioning_Tensor_Assembly.py"
C4_BLOB = "c6e994f6877550080fb4505c370ba46b354b3bcc"

C18 = "PAD_Stream_V16C18_Conditioning_to_Y_Transport_Alignment_and_Training_Dataset_Certification.py"
C18_BLOB = "b97cef8f01cf296abb446d70db739227e97de56d"

C26 = (
    "PAD_Stream_V16C26_EXP2_Physics_Informed_Training_Execution_"
    "Best_Validation_Checkpoint_and_Locked_Test_Evaluation.py"
)
C26_BLOB = "62e19e6b502fb3ab101a2589251c26b5f9ad9031"

D22 = (
    "PAD_Stream_V16D22_Versioned_InjectionRate_ProducerBHP_"
    "ControlSpace_Design_and_New_FoundationCase_Registry_Contract.py"
)
D22_BLOB = "d1c4a9e737ce59ed4450dbbb61859247986ceada"

D23 = "PAD_Stream_V16D23_Generate_and_Certify_Fresh_Recipe1p1_Geologies_0026_0029.py"
D23_BLOB = "e4c9fa6988040b6a2034717b12ea1831eb345e95"

D32 = (
    "PAD_Stream_V16D32_ControlSpace_36Case_Stage4_"
    "Learning_Dataset_and_TRAIN_Only_Normalization.py"
)
D32_BLOB = "80a346fdb2c4d03997b68e4ee8655c34cfcc53e4"

SOURCE_BLOBS = {
    R7R7E_FREEZE: R7R7E_FREEZE_BLOB,
    AV1E: AV1E_BLOB,
    R8R: R8R_BLOB,
    SG5: SG5_BLOB,
    C2: C2_BLOB,
    C4: C4_BLOB,
    C18: C18_BLOB,
    C26: C26_BLOB,
    D22: D22_BLOB,
    D23: D23_BLOB,
    D32: D32_BLOB,
}

BASE = Path("post_v16") / RID / "POSTV16_AV1_Physics_vs_PIRNN_ConstantPhi"

R7R7E_FREEZE_REL = (
    BASE / "POSTV16_AV1_D_R7_R7E_Scientific_PASS_Outcome_Freeze"
)
R7R7E_FREEZE_SUMMARY = "PAD_Stream_POSTV16_AV1_D_R7_R7E_Outcome_Freeze_Summary.json"
R7R7E_FREEZE_MANIFEST = "POSTV16_AV1_D_R7_R7E_Outcome_Freeze_Artifact_Manifest.csv"

AV1E_REL = (
    BASE /
    "POSTV16_AV1_E_Prospective_External_Full_Physics_"
    "Deployment_Acceptance_Contract_Freeze"
)
AV1E_SUMMARY = "PAD_Stream_POSTV16_AV1_E_Summary.json"
AV1E_MANIFEST = "POSTV16_AV1_E_Artifact_Manifest.csv"

OUT_REL = (
    Path("post_v16")
    / RID
    / "POSTV16_AV2_Variable_Porosity"
    / "POSTV16_AV2_A0_Variable_Porosity_Authority_Gap_and_Physics_Impact_Freeze"
)
BLOCKED_REL = (
    Path("post_v16")
    / RID
    / "POSTV16_AV2_Variable_Porosity"
    / "POSTV16_AV2_A0_BLOCKED"
)

AV1_R7R7E_FREEZE_STATUS = (
    "AV1DR7R7E_FOUNDATION0001_SCIENTIFIC_PASS_OUTCOME_FROZEN_"
    "NO_SUBSEQUENT_MILESTONE_AUTHORIZED"
)
AV1E_STATUS = (
    "AV1E_EXTERNAL_FULL_PHYSICS_DEPLOYMENT_ACCEPTANCE_CONTRACT_"
    "PROSPECTIVELY_FROZEN_NO_BENCHMARK_EXECUTION"
)

FOUNDATION_SHA = "4239e412ca6e2780f108c8eb1b0252e80a56be305bce48cc58e50d6140b86acc"
AV1_INTEGRATED_STATE_SHA = "24e053237d8bd21bdfd0db72f97fd38ae2c2caa77b0ab812b6c36337020d5bd8"

CANONICAL_DAYS = [30.0, 60.0, 100.0, 150.0, 250.0, 365.0, 500.0, 750.0, 1000.0]
GRID = [15, 50, 50]
AV1_POROSITY = 0.20


class GateError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def git_text(root: Path, *args: str) -> str:
    p = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return p.stdout.strip()


def git_blob_sha(path: Path, root: Path) -> str:
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
        raise GateError("manifest_empty")
    for fn, expected in manifest.items():
        p = directory / fn
        if not p.is_file():
            raise GateError(f"manifest_missing:{fn}")
        actual = sha256_file(p)
        if actual != expected:
            raise GateError(f"manifest_SHA:{fn}:{actual}:{expected}")
    return manifest


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
            raise GateError(f"existing_output_differs:{name}")
        if not p.exists():
            p.write_bytes(data)


def source_text(root: Path, name: str) -> str:
    p = root / name
    if not p.is_file():
        raise GateError(f"source_missing:{name}")
    return p.read_text(encoding="utf-8", errors="replace")


def contains_all(text: str, tokens: list[str]) -> bool:
    return all(token in text for token in tokens)


def self_test() -> None:
    # Pure AV2 dependency map sanity.
    affected = {
        "pressure_operator": False,
        "Darcy_volumetric_flux": False,
        "pore_velocity": True,
        "Pollock_kinematics_or_TOF": True,
        "PI_RNN_porosity_conditioning": True,
        "pore_volume_and_mass_capacity": True,
        "EOS_mass_to_saturation_mapback": True,
    }
    if sum(bool(v) for v in affected.values()) != 5:
        raise RuntimeError("AV2_dependency_map")
    if affected["pressure_operator"]:
        raise RuntimeError("AV2_pressure_scope")
    print("POSTV16-AV2-A0 variable-porosity scope self-test: PASS")


def main(root: Path, drive: Path) -> int:
    gates: dict[str, dict[str, Any]] = {}
    stage = "preflight"
    out = drive / OUT_REL
    blocked = drive / BLOCKED_REL

    def gate(name: str, passed: Any, value: Any = None) -> None:
        ok = bool(passed)
        gates[name] = {"passed": ok, "value": value}
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {value}" if value is not None else ""))
        if not ok:
            raise GateError(name)

    print("=" * 196)
    print("POSTV16-AV2-A0 — VARIABLE-POROSITY AUTHORITY GAP + PHYSICS-IMPACT DESIGN/FREEZE")
    print("=" * 196)
    print("DESIGN/AUDIT/FREEZE ONLY. NO VARIABLE-POROSITY FIELD GENERATION.")
    print("NO PRESSURE SOLVE. NO DARCY SOLVE. NO POLLOCK RETRACING. NO TRANSPORT GENERATION.")
    print("NO TRAINING. NO INFERENCE. NO MAPBACK. NO CMG / EXTERNAL VALIDATION.")
    print("AV1 REMAINS FROZEN. AV1-E EXTERNAL-VALIDATION CONTRACT REMAINS VALID BUT DEFERRED UNTIL AV1-AV5 SYSTEM BUILDOUT IS COMPLETE.\n")

    try:
        root = root.resolve()
        drive = drive.resolve()

        parent = git_text(root, "rev-parse", "HEAD^")
        status = git_text(root, "status", "--porcelain")

        gate(
            "repository_parent_is_AV1E_commit",
            parent == PARENT_AV1E_COMMIT,
            parent,
        )
        gate("repository_clean", status == "", repr(status))

        for fn, expected in SOURCE_BLOBS.items():
            p = root / fn
            actual = git_blob_sha(p, root) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact", actual == expected, actual)

        # ------------------------------------------------------------------
        # Bind AV1 successful end-to-end outcome.
        # ------------------------------------------------------------------
        stage = "AV1_outcome_binding"

        av1 = drive / R7R7E_FREEZE_REL
        gate("AV1_R7R7E_outcome_freeze_present", av1.is_dir(), str(av1))
        av1_manifest = verify_manifest(av1, R7R7E_FREEZE_MANIFEST)
        gate("AV1_R7R7E_manifest_SHA_closure", True, len(av1_manifest))

        av1_summary = load_json(av1 / R7R7E_FREEZE_SUMMARY)

        gate(
            "AV1_R7R7E_freeze_status_exact",
            av1_summary["status"] == AV1_R7R7E_FREEZE_STATUS,
            av1_summary["status"],
        )
        gate("AV1_scientific_PASS_preserved", av1_summary["R7R7E_scientific_execution_pass"] is True)
        gate("AV1_all_9_times_completed", av1_summary["R7R7E_all_9_times_completed"] is True)
        gate("AV1_integrated_state_SHA_exact", av1_summary["R7R7E_integrated_state_sha256"] == AV1_INTEGRATED_STATE_SHA)
        gate("AV1_plume_fidelity_claim_false", av1_summary["plume_fidelity_claim"] is False)
        gate("AV1_generalization_claim_false", av1_summary["generalization_claim"] is False)

        # ------------------------------------------------------------------
        # Bind but defer the external-validation branch.
        # ------------------------------------------------------------------
        stage = "AV1E_deferred_external_validation_binding"

        av1e = drive / AV1E_REL
        gate("AV1E_contract_output_present", av1e.is_dir(), str(av1e))
        av1e_manifest = verify_manifest(av1e, AV1E_MANIFEST)
        gate("AV1E_manifest_SHA_closure", True, len(av1e_manifest))
        av1e_summary = load_json(av1e / AV1E_SUMMARY)

        gate("AV1E_status_exact", av1e_summary["status"] == AV1E_STATUS, av1e_summary["status"])
        gate("AV1E_thresholds_frozen_before_benchmark", av1e_summary["thresholds_frozen_before_benchmark_exposure"] is True)
        gate("AV1E_benchmark_not_executed", av1e_summary["external_benchmark_execution_performed"] is False)
        gate("AV1E_benchmark_not_read", av1e_summary["external_benchmark_results_read"] is False)

        # ------------------------------------------------------------------
        # Source-level porosity authority audit.
        # ------------------------------------------------------------------
        stage = "porosity_authority_audit"

        r8r = source_text(root, R8R)
        sg5 = source_text(root, SG5)
        c2 = source_text(root, C2)
        c4 = source_text(root, C4)
        c18 = source_text(root, C18)
        c26 = source_text(root, C26)
        d22 = source_text(root, D22)
        d23 = source_text(root, D23)
        d32 = source_text(root, D32)

        gate(
            "Foundation0001_porosity_constructed_as_constant_field",
            contains_all(
                r8r,
                [
                    "porosity = np.full_like(K, poro_value",
                    '"derivation": f"constant porosity = {poro_value}',
                ],
            ),
        )

        gate(
            "SG5_constant_porosity_exact_0p20",
            "POROSITY = 0.20" in sg5,
        )

        gate(
            "SG5_pore_velocity_explicitly_depends_on_porosity",
            contains_all(
                sg5,
                [
                    "v = q / (A * phi)",
                    "vx = qx / (AX_M2 * POROSITY)",
                    "vy = qy / (AY_M2 * POROSITY)",
                    "vz = qz / (AZ_M2 * POROSITY)",
                ],
            ),
        )

        gate(
            "C2_requires_porosity_grid_channel",
            '"Kx", "Ky", "Kz", "porosity", "pressure"' in c2,
        )

        gate(
            "C4_required_channel_5_is_porosity",
            contains_all(
                c4,
                [
                    "5: porosity",
                    "phi = np.asarray(db[\"porosity\"]",
                    "phi,",
                ],
            ),
        )

        gate(
            "C18_training_dataset_uses_frozen_C4_conditioning",
            contains_all(
                c18,
                [
                    "C4_NAME=\"V16C4_Model_Ready_Conditioning_Tensors.npz\"",
                    'xr=np.asarray(z["X_sequence_required"]',
                ],
            ),
        )

        gate(
            "C26_consumes_nine_channel_C18_training_dataset",
            contains_all(
                c26,
                [
                    "X7=np.asarray(d[\"X_sequence_required\"]",
                    "X=np.concatenate([X7,T,eta_seq[:,:,None]],axis=2)",
                    "X.shape==(9702,201,9)",
                ],
            ),
        )

        gate(
            "D22_controlspace_explicitly_fixed_porosity_0p20",
            '"porosity":0.20' in d22,
        )

        gate(
            "D23_generated_porosity_is_constant_0p20",
            contains_all(
                d23,
                [
                    "phi=np.full_like(K,.2)",
                    '"porosity_0p2"',
                ],
            ),
        )

        gate(
            "D32_interface_contains_porosity_channel",
            '"porosity",' in d32,
        )

        gate(
            "D32_binds_D23_geology_authority",
            contains_all(
                d32,
                [
                    "Fresh Recipe1.1 geology authority: K + porosity.",
                    "V16_D23_FRESH_RECIPE1P1_GEOLOGIES_0026_0029",
                ],
            ),
        )

        # The key scientific closure of A0:
        # interface support exists, but no audited heterogeneous-phi source
        # authority exists in the bound AV1/C26/D23 lineage.
        gate(
            "variable_porosity_interface_exists",
            True,
        )
        gate(
            "bound_training_geology_porosity_was_constant",
            True,
        )
        gate(
            "heterogeneous_porosity_authority_not_yet_established",
            True,
        )
        gate(
            "AV1_C26_checkpoint_not_promoted_as_AV2_variable_phi_authority",
            True,
        )

        # ------------------------------------------------------------------
        # Freeze AV2 scope, affected operators, and milestone plan.
        # ------------------------------------------------------------------
        stage = "freeze_AV2_A0"

        scientific_question = (
            "Holding the accepted AV1 permeability field, grid, wells, controls, "
            "fluid/EOS, relative-permeability/Corey laws, capillary model, and "
            "conservative reconciliation semantics fixed, can PAD-Stream introduce "
            "spatially variable porosity consistently through pore velocity, "
            "Pollock/TOF kinematics, PI-RNN conditioning, pore-volume/component-mass "
            "capacity, EOS inversion, and conservative mapback while remaining "
            "bounded and conservative across all nine canonical times?"
        )

        impact_rows = [
            {
                "component": "finite_volume_pressure_operator",
                "AV2_expected_direct_phi_dependency": False,
                "AV2_rule": (
                    "Keep the AV1 pressure equation/operator unchanged. "
                    "Future execution must verify whether the computed pressure "
                    "is numerically identical when only porosity changes."
                ),
            },
            {
                "component": "Darcy_volumetric_face_fluxes_Q",
                "AV2_expected_direct_phi_dependency": False,
                "AV2_rule": (
                    "Keep AV1 transmissibility/K/fluid/well controls fixed. "
                    "Future execution audits Q identity if pressure is unchanged."
                ),
            },
            {
                "component": "face_pore_velocity",
                "AV2_expected_direct_phi_dependency": True,
                "AV2_rule": (
                    "Replace constant phi=0.20 conversion with a prospectively "
                    "frozen spatial face-porosity rule; velocity must be recomputed."
                ),
            },
            {
                "component": "Pollock_streamlines_and_TOF",
                "AV2_expected_direct_phi_dependency": True,
                "AV2_rule": (
                    "Do not reuse AV1 trajectories/TOF by assumption. "
                    "Retrace/recompute under AV2 pore velocities and audit geometry, "
                    "capture, terminal TOF, and weights."
                ),
            },
            {
                "component": "PI_RNN_conditioning",
                "AV2_expected_direct_phi_dependency": True,
                "AV2_rule": (
                    "Porosity remains the existing sequence channel, but AV2 requires "
                    "new variable-phi TRAIN/VALIDATION/LOCKED-OOD evidence before "
                    "a checkpoint can be accepted as variable-porosity authority."
                ),
            },
            {
                "component": "cell_pore_volume_and_component_mass_capacity",
                "AV2_expected_direct_phi_dependency": True,
                "AV2_rule": (
                    "Use cell-local phi*cell_bulk_volume. Recompute S0 and H1 physical "
                    "component-mass capacities under the unchanged R2 EOS."
                ),
            },
            {
                "component": "conservative_mapback_and_EOS_inversion",
                "AV2_expected_direct_phi_dependency": True,
                "AV2_rule": (
                    "Preserve the R7-R7D/R7-R7E reconciliation semantics but recompute "
                    "capacity and mass-to-saturation inversion with AV2 local pore volume."
                ),
            },
        ]

        freeze = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "protocol_id": PROTOCOL_ID,
            "scientific_question": scientific_question,
            "AV_series_position": {
                "AV1": "CLOSED — heterogeneous K, constant phi",
                "AV2": "ACTIVE — heterogeneous K, spatially variable phi",
                "AV3": "FUTURE — spatial Corey/relative-permeability heterogeneity",
                "AV4": "FUTURE — pressure-refresh/dynamic-flow sensitivity",
                "AV5": "FUTURE — final integrated system/performance validation",
                "external_CMG_validation": "DEFERRED until AV1-AV5 buildout is complete",
            },
            "AV1_frozen_authorities": {
                "Foundation_Case_0001_SHA256": FOUNDATION_SHA,
                "AV1_integrated_state_SHA256": AV1_INTEGRATED_STATE_SHA,
                "Kx_Ky_Kz": "UNCHANGED in AV2 controlled-isolation experiment",
                "grid": GRID,
                "canonical_days": CANONICAL_DAYS,
                "well_geometry_and_controls": "UNCHANGED initially",
                "fluid_and_EOS": "UNCHANGED",
                "relative_permeability_and_Corey": "UNCHANGED",
                "capillary_model": "UNCHANGED",
                "saturation_bounds": [0.20, 0.80],
                "R7R7D_terminal_halo_protocol_semantics": "PRESERVED",
                "R7R7E_exact_S0_H1_D1_cell_identity": (
                    "NOT frozen because Pollock trajectories may change with spatial phi"
                ),
            },
            "authority_audit": {
                "Foundation0001_phi": 0.20,
                "V16D22_phi": 0.20,
                "V16D23_phi": 0.20,
                "porosity_channel_present_in_C2_C4_D32": True,
                "heterogeneous_phi_training_authority_present": False,
                "accepted_AV1_C26_checkpoint_is_AV2_variable_phi_authority": False,
                "interpretation": (
                    "The software/data interfaces already carry porosity, but the bound "
                    "AV1/C26 and V16D-22/23 lineages audited here do not provide training "
                    "variation in porosity. AV2 therefore requires a new prospective "
                    "variable-porosity experiment rather than a silent reuse claim."
                ),
            },
            "AV2_controlled_delta": {
                "new_physics_variable": "spatial porosity phi(k,j,i)",
                "permeability_field_changed": False,
                "well_controls_changed": False,
                "fluid_EOS_changed": False,
                "Corey_relperm_changed": False,
                "capillary_model_changed": False,
                "porosity_field_changed": True,
            },
            "checkpoint_policy": {
                "AV1_C26_checkpoint_role": "frozen AV1 baseline/comparator only",
                "AV1_C26_direct_variable_phi_promotion": False,
                "new_AV2_training_required_before_variable_phi_checkpoint_acceptance": True,
                "new_split_firewall_required": True,
                "new_locked_OOD_porosity_identity_required": True,
                "no_AV1_checkpoint_retuning_on_AV2_locked_OOD": True,
            },
            "external_validation_policy": {
                "AV1E_contract_remains_valid": True,
                "AV1F_execution_now": False,
                "CMG_validation_now": False,
                "reason": (
                    "Complete the internal AV1->AV5 PAD-Stream system first; "
                    "validate the finished system externally afterward."
                ),
            },
            "next": {
                "milestone": "POSTV16-AV2-A1",
                "name": (
                    "Prospective Spatial-Porosity Field Model, Bounds, "
                    "Correlation, and Split-Registry Freeze"
                ),
                "authorized": True,
                "field_generation_in_A0": False,
                "training_in_A0": False,
                "inference_in_A0": False,
            },
        }

        plan = {
            "AV2_A0": "Scope / authority-gap / physics-impact freeze — current milestone",
            "AV2_A1": (
                "Prospectively freeze variable-porosity field construction, physical "
                "bounds, K-phi relation or independence choice, mean/pore-volume policy, "
                "realization registry, TRAIN/VALIDATION/LOCKED-OOD split."
            ),
            "AV2_A2": (
                "Generate and certify phi realizations; rebuild pore velocities, "
                "Pollock trajectories and TOF; audit pressure/Q invariance where expected."
            ),
            "AV2_A3": (
                "Assemble variable-phi transport teacher/dataset and freeze the "
                "PI-RNN objective/normalization/architecture/split contract."
            ),
            "AV2_A4": (
                "Train, validate, select checkpoint, and perform one-touch locked-OOD "
                "variable-phi evaluation."
            ),
            "AV2_A5": (
                "Promote accepted AV2 checkpoint into PAD-Stream and integrate local "
                "pore-volume capacity with frozen R7D terminal-halo semantics."
            ),
            "AV2_A6": (
                "Execute end-to-end nine-time AV2 Foundation Case variable-porosity "
                "integration; boundedness, conservation, EOS, and mapback certification."
            ),
            "AV2_A7": (
                "Freeze AV2 outcome and hand off to AV3 spatial Corey/rel-perm heterogeneity."
            ),
        }

        summary = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "protocol_id": PROTOCOL_ID,
            "scientific_question": scientific_question,
            "AV1_R7R7E_PASS_bound": True,
            "AV1E_external_validation_contract_bound_but_deferred": True,
            "Foundation0001_porosity": AV1_POROSITY,
            "variable_porosity_interface_exists": True,
            "heterogeneous_porosity_authority_present_in_bound_lineage": False,
            "AV1_C26_promoted_as_AV2_checkpoint": False,
            "AV2_requires_new_variable_phi_learning_evidence": True,
            "AV2_field_generated": False,
            "pressure_solve_executed": False,
            "Darcy_solve_executed": False,
            "Pollock_execution": False,
            "training": False,
            "inference": False,
            "mapback": False,
            "CMG_validation": False,
            "next": freeze["next"],
        }

        immutable_publish(
            out,
            {
                "PAD_Stream_POSTV16_AV2_A0_Summary.json": json_bytes(summary),
                "POSTV16_AV2_A0_Variable_Porosity_Scope_and_Authority_Gap_Freeze.json": json_bytes(freeze),
                "POSTV16_AV2_A0_Physics_Impact_Matrix.csv": csv_bytes(impact_rows),
                "POSTV16_AV2_A0_Development_Milestone_Plan.json": json_bytes(plan),
                "POSTV16_AV2_A0_Final_Gate_Matrix.csv": csv_bytes(
                    [{"gate": k, **v} for k, v in gates.items()]
                ),
            },
        )

        manifest_rows = []
        for q in sorted(out.iterdir()):
            if q.is_file() and q.name != "POSTV16_AV2_A0_Artifact_Manifest.csv":
                manifest_rows.append(
                    {
                        "file": q.name,
                        "sha256": sha256_file(q),
                        "bytes": q.stat().st_size,
                    }
                )
        immutable_publish(
            out,
            {
                "POSTV16_AV2_A0_Artifact_Manifest.csv": csv_bytes(manifest_rows)
            },
        )

        print("\n" + "=" * 196)
        print("POSTV16-AV2-A0: PASS")
        print("=" * 196)
        print(f"{'Status':116}: {STATUS_PASS}")
        print(f"{'Scientific question frozen':116}: True")
        print(f"{'AV1 constant-phi end-to-end PASS preserved':116}: True")
        print(f"{'AV1-E external-validation contract preserved but deferred':116}: True")
        print(f"{'Foundation0001 phi':116}: {AV1_POROSITY}")
        print(f"{'Variable-phi interface already present':116}: True")
        print(f"{'Heterogeneous-phi training authority already present':116}: False")
        print(f"{'AV1 C26 promoted as AV2 variable-phi checkpoint':116}: False")
        print(f"{'AV2 requires new variable-phi learning evidence':116}: True")
        print(f"{'K / wells / controls / EOS / relperm / capillary changed in A0':116}: False")
        print(f"{'Variable-phi field generated in A0':116}: False")
        print(f"{'Pressure / Darcy / Pollock / training / inference / mapback':116}: False / False / False / False / False / False")
        print(f"{'CMG validation executed':116}: False")
        print(f"{'Next milestone authorized':116}: True")
        print(f"{'NEXT':116}: POSTV16-AV2-A1 — prospective spatial-porosity field-model and split-registry freeze")
        print("=" * 196)
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": MILESTONE,
            "status": STATUS_BLOCKED,
            "failed_stage": stage,
            "exception": repr(exc),
            "gates": gates,
            "variable_porosity_field_generated": False,
            "training": False,
            "inference": False,
            "mapback": False,
            "CMG_validation": False,
            "AV1_result_changed": False,
            "AV1E_contract_changed": False,
            "next_milestone_authorized": False,
            "next_action": (
                "Audit only the AV2-A0 scope/authority binding. Do not generate a "
                "porosity field or train a variable-phi model until A0 is validly frozen."
            ),
        }
        data = json_bytes(report)
        q = blocked / "POSTV16_AV2_A0_Blocked_Report.json"
        if q.exists() and q.read_bytes() != data:
            q = blocked / (
                "POSTV16_AV2_A0_Blocked_Report_"
                + hashlib.sha256(data).hexdigest()[:12]
                + ".json"
            )
        if not q.exists():
            q.write_bytes(data)

        print("\n" + "=" * 196)
        print("POSTV16-AV2-A0: BLOCKED")
        print("=" * 196)
        print("Failed stage:", stage)
        print("Exception   :", repr(exc))
        print("Report      :", q)
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
