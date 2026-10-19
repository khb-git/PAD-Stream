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


MILESTONE = "POSTV16-AV2-A1"
STATUS_PASS = (
    "AV2A1_SPATIAL_POROSITY_FIELD_MODEL_BOUNDS_CORRELATION_"
    "FACE_RULE_AND_SPLIT_REGISTRY_PROSPECTIVELY_FROZEN_NO_FIELD_GENERATION"
)
STATUS_BLOCKED = "AV2A1_SPATIAL_POROSITY_FIELD_MODEL_FREEZE_BLOCKED"
PROTOCOL_ID = (
    "POSTV16_AV2_A1_SPATIAL_POROSITY_FIELD_MODEL_AND_SPLIT_REGISTRY_V1"
)

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"

# A1 must be committed directly on top of the exact A0 scope freeze.
PARENT_AV2A0_COMMIT = "50d7ac5c4c3f268fa249a2b99270021bbf67b90d"

A0 = (
    "PAD_Stream_POSTV16_AV2_A0_"
    "Variable_Porosity_Authority_Gap_and_Physics_Impact_Freeze.py"
)
A0_BLOB = "692003766ad54ec7f18062ad52e15a9d4b71544b"

TRANSFORM = "transform_sgsim_perm.py"
TRANSFORM_BLOB = "c502c1f29c87a0e2f65ff3cf95bd2f414103adf3"

D23 = "PAD_Stream_V16D23_Generate_and_Certify_Fresh_Recipe1p1_Geologies_0026_0029.py"
D23_BLOB = "e4c9fa6988040b6a2034717b12ea1831eb345e95"

SG5 = "PAD_Stream_V15SG5_Exact_Pollock_Streamlines.py"
SG5_BLOB = "9a0b64ea7e669904d0d9855ade1c6b052f05ecea"

C4 = "PAD_Stream_V16C4_Model_Ready_Conditioning_Tensor_Assembly.py"
C4_BLOB = "c6e994f6877550080fb4505c370ba46b354b3bcc"

GAUSS = "SGSIM_50x50x15_GAUSS.csv"
GAUSS_BLOB = "56c87fed8b1e9fd7f6d3451be21a63659e6fa4bf"

PERM = "SGSIM_50x50x15_PERM_MD.csv"
PERM_BLOB = "317dd47d458bc6f880c2e3dc4ec1f69eeb0dd314"

SOURCE_BLOBS = {
    A0: A0_BLOB,
    TRANSFORM: TRANSFORM_BLOB,
    D23: D23_BLOB,
    SG5: SG5_BLOB,
    C4: C4_BLOB,
    GAUSS: GAUSS_BLOB,
    PERM: PERM_BLOB,
}

BASE_A0 = (
    Path("post_v16")
    / RID
    / "POSTV16_AV2_Variable_Porosity"
    / "POSTV16_AV2_A0_Variable_Porosity_Authority_Gap_and_Physics_Impact_Freeze"
)

A0_SUMMARY = "PAD_Stream_POSTV16_AV2_A0_Summary.json"
A0_FREEZE = "POSTV16_AV2_A0_Variable_Porosity_Scope_and_Authority_Gap_Freeze.json"
A0_PLAN = "POSTV16_AV2_A0_Development_Milestone_Plan.json"
A0_MANIFEST = "POSTV16_AV2_A0_Artifact_Manifest.csv"

OUT_REL = (
    Path("post_v16")
    / RID
    / "POSTV16_AV2_Variable_Porosity"
    / "POSTV16_AV2_A1_Spatial_Porosity_Field_Model_and_Split_Registry_Freeze"
)

BLOCKED_REL = (
    Path("post_v16")
    / RID
    / "POSTV16_AV2_Variable_Porosity"
    / "POSTV16_AV2_A1_BLOCKED"
)

A0_STATUS = (
    "AV2A0_VARIABLE_POROSITY_SCIENTIFIC_SCOPE_AUTHORITY_GAP_AND_"
    "PHYSICS_IMPACT_PROSPECTIVELY_FROZEN_NO_EXECUTION"
)

# ----------------------------------------------------------------------
# FROZEN AV2-A1 DESIGN CHOICES
# ----------------------------------------------------------------------

GRID = [15, 50, 50]
DX_FT = 20.0
DY_FT = 20.0
DZ_FT = 4.0

PHI_CENTER = 0.20
PHI_HALF_RANGE = 0.10
PHI_MIN_OPEN = 0.10
PHI_MAX_OPEN = 0.30
PHI_TRANSFORM_SCALE = 2.0

LATENT_K_PHI_CORRELATION = 0.60

MAJOR_RANGE_FT = 200.0
MINOR_RANGE_FT = 200.0
VERTICAL_RANGE_FT = 15.0
AZIMUTH_DEG = 30.0
COVARIANCE_MODEL = "exponential"
COVARIANCE_FORM = "C(h*) = exp(-3 h*)"
PERIODIC_MINIMUM_IMAGE = True

FACE_POROSITY_RULE = "arithmetic_mean_of_adjacent_cell_porosity"
FACE_POROSITY_FORMULA = "phi_face = 0.5 * (phi_left + phi_right)"

CANONICAL_DAYS = [
    30.0, 60.0, 100.0, 150.0, 250.0,
    365.0, 500.0, 750.0, 1000.0,
]

INJECTION_TPD = 500.0
PRODUCER_BHP_PSI = 2000.0

REALIZATION_REGISTRY = [
    {
        "porosity_realization_id": "AV2PHI0001",
        "seed": 260201,
        "partition": "TRAIN",
        "locked_until": "N/A",
    },
    {
        "porosity_realization_id": "AV2PHI0002",
        "seed": 260202,
        "partition": "TRAIN",
        "locked_until": "N/A",
    },
    {
        "porosity_realization_id": "AV2PHI0003",
        "seed": 260203,
        "partition": "VALIDATION",
        "locked_until": "N/A",
    },
    {
        "porosity_realization_id": "AV2PHI0004",
        "seed": 260204,
        "partition": "LOCKED_OOD_TEST",
        "locked_until": "AV2 checkpoint frozen after TRAIN/VALIDATION selection",
    },
]


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
            raise GateError(f"existing_output_differs:{name}")
        if not p.exists():
            p.write_bytes(data)


def source_text(root: Path, name: str) -> str:
    p = root / name
    if not p.is_file():
        raise GateError(f"source_missing:{name}")
    return p.read_text(encoding="utf-8", errors="replace")


def self_test() -> None:
    ids = [r["porosity_realization_id"] for r in REALIZATION_REGISTRY]
    seeds = [r["seed"] for r in REALIZATION_REGISTRY]
    parts = [r["partition"] for r in REALIZATION_REGISTRY]

    if len(ids) != len(set(ids)):
        raise RuntimeError("duplicate_porosity_realization_id")
    if len(seeds) != len(set(seeds)):
        raise RuntimeError("duplicate_porosity_seed")
    if parts.count("TRAIN") != 2:
        raise RuntimeError("TRAIN_count")
    if parts.count("VALIDATION") != 1:
        raise RuntimeError("VALIDATION_count")
    if parts.count("LOCKED_OOD_TEST") != 1:
        raise RuntimeError("LOCKED_OOD_count")

    # Representative finite latent values remain strictly inside the analytical
    # asymptotic bounds. Extremely large |g| can round tanh to +/-1 in IEEE
    # floating point even though the mathematical transform is open-bounded.
    for g in (-6.0, -2.0, 0.0, 2.0, 6.0):
        phi = PHI_CENTER + PHI_HALF_RANGE * math.tanh(g / PHI_TRANSFORM_SCALE)
        if not (PHI_MIN_OPEN < phi < PHI_MAX_OPEN):
            raise RuntimeError(("phi_bounds", g, phi))

    if not (0.0 < LATENT_K_PHI_CORRELATION < 1.0):
        raise RuntimeError("rho_invalid")

    print("POSTV16-AV2-A1 spatial-porosity freeze self-test: PASS")


def main(root: Path, drive: Path) -> int:
    gates: dict[str, dict[str, Any]] = {}
    stage = "preflight"

    out = drive / OUT_REL
    blocked = drive / BLOCKED_REL

    def gate(name: str, passed: Any, value: Any = None) -> None:
        ok = bool(passed)
        gates[name] = {"passed": ok, "value": value}
        suffix = f" — {value}" if value is not None else ""
        print(f"[{'PASS' if ok else 'FAIL'}] {name}{suffix}")
        if not ok:
            raise GateError(name)

    print("=" * 196)
    print("POSTV16-AV2-A1 — SPATIAL-POROSITY FIELD MODEL + BOUNDS + CORRELATION + SPLIT-REGISTRY FREEZE")
    print("=" * 196)
    print("PROSPECTIVE DESIGN/FREEZE ONLY.")
    print("NO POROSITY FIELD IS GENERATED. NO SEED IS PRETESTED. NO REALIZATION IS REJECTED OR RESEEDED.")
    print("NO PRESSURE/DARCY/POLLOCK/TRANSPORT EXECUTION. NO TRAINING. NO INFERENCE. NO MAPBACK. NO CMG.")
    print("THE AV1 PERMEABILITY FIELD REMAINS EXACTLY FROZEN.\n")

    try:
        root = root.resolve()
        drive = drive.resolve()

        parent = git_text(root, "rev-parse", "HEAD^")
        status = git_text(root, "status", "--porcelain")

        gate(
            "repository_parent_is_AV2A0_commit",
            parent == PARENT_AV2A0_COMMIT,
            parent,
        )
        gate("repository_clean", status == "", repr(status))

        for fn, expected in SOURCE_BLOBS.items():
            p = root / fn
            actual = git_blob_sha(p, root) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact", actual == expected, actual)

        # ------------------------------------------------------------------
        # Bind AV2-A0 outcome and authorization.
        # ------------------------------------------------------------------
        stage = "AV2A0_binding"

        a0 = drive / BASE_A0
        gate("AV2A0_output_present", a0.is_dir(), str(a0))

        a0_manifest = verify_manifest(a0, A0_MANIFEST)
        gate("AV2A0_manifest_SHA_closure", True, len(a0_manifest))

        summary0 = load_json(a0 / A0_SUMMARY)
        freeze0 = load_json(a0 / A0_FREEZE)
        plan0 = load_json(a0 / A0_PLAN)

        gate("AV2A0_status_exact", summary0["status"] == A0_STATUS, summary0["status"])
        gate("AV2A0_variable_phi_interface_present", summary0["variable_porosity_interface_exists"] is True)
        gate(
            "AV2A0_heterogeneous_phi_authority_absent",
            summary0["heterogeneous_porosity_authority_present_in_bound_lineage"] is False,
        )
        gate("AV2A0_C26_not_promoted", summary0["AV1_C26_promoted_as_AV2_checkpoint"] is False)
        gate("AV2A0_new_learning_evidence_required", summary0["AV2_requires_new_variable_phi_learning_evidence"] is True)
        gate("AV2A1_authorized_by_A0", freeze0["next"]["authorized"] is True)
        gate("AV2A1_next_id_exact", freeze0["next"]["milestone"] == "POSTV16-AV2-A1")
        gate("AV2A0_plan_contains_A1", "AV2_A1" in plan0)

        # ------------------------------------------------------------------
        # Source-level geology / kinematics anchors.
        # ------------------------------------------------------------------
        stage = "source_semantic_binding"

        transform = source_text(root, TRANSFORM)
        d23 = source_text(root, D23)
        sg5 = source_text(root, SG5)
        c4 = source_text(root, C4)

        gate(
            "original_SGSim_Gaussian_authority_bound",
            "SGSIM_50x50x15_GAUSS.csv" in transform,
        )
        gate(
            "original_AV1_permeability_authority_bound",
            "SGSIM_50x50x15_PERM_MD.csv" in transform,
        )
        gate(
            "D23_exponential_covariance_form_present",
            "return np.exp(-3.0*hstar)" in d23,
        )
        gate(
            "D23_200ft_200ft_15ft_continuity_present",
            (
                "A_MAJOR=200.0" in d23
                and "A_MINOR=200.0" in d23
                and "A_VERT=15.0" in d23
            ),
        )
        gate(
            "SG5_constant_phi_pore_velocity_source_bound",
            (
                "POROSITY = 0.20" in sg5
                and "vx = qx / (AX_M2 * POROSITY)" in sg5
            ),
        )
        gate(
            "C4_porosity_channel_preserved",
            (
                "5: porosity" in c4
                and 'phi = np.asarray(db["porosity"]' in c4
            ),
        )

        # ------------------------------------------------------------------
        # Freeze the new AV2 porosity design.
        # ------------------------------------------------------------------
        stage = "freeze_A1_contract"

        field_model = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "protocol_id": PROTOCOL_ID,
            "role": (
                "Prospective synthetic variable-porosity design for AV2 only. "
                "It is not represented as recovered historical porosity data "
                "or as a field-calibrated porosity model."
            ),
            "controlled_isolation": {
                "AV1_permeability_field": "UNCHANGED EXACTLY",
                "Kx_Ky_Kz_changed": False,
                "well_geometry_changed": False,
                "well_controls_changed": False,
                "fluid_EOS_changed": False,
                "Corey_relperm_changed": False,
                "capillary_model_changed": False,
                "only_new_geological_property": "porosity",
            },
            "grid": {
                "shape_kji": GRID,
                "dx_ft": DX_FT,
                "dy_ft": DY_FT,
                "dz_ft": DZ_FT,
            },
            "permeability_latent_anchor": {
                "source": GAUSS,
                "source_git_blob": GAUSS_BLOB,
                "treatment": (
                    "Load the exact original SGSim Gaussian field and standardize "
                    "the 37,500-cell sample to zero mean and unit standard deviation. "
                    "This standardized field is Z_K and is NOT used to regenerate K."
                ),
                "K_remains_from": PERM,
                "K_git_blob": PERM_BLOB,
            },
            "porosity_residual_generator": {
                "type": "deterministic_periodic_spectral_Gaussian_random_field",
                "historical_SGSim_claim": False,
                "covariance_model": COVARIANCE_MODEL,
                "covariance_form": COVARIANCE_FORM,
                "major_range_ft": MAJOR_RANGE_FT,
                "minor_range_ft": MINOR_RANGE_FT,
                "vertical_range_ft": VERTICAL_RANGE_FT,
                "azimuth_deg": AZIMUTH_DEG,
                "periodic_minimum_image": PERIODIC_MINIMUM_IMAGE,
                "new_AV2_design_choice": True,
            },
            "K_phi_latent_coupling": {
                "target_latent_Pearson_correlation": LATENT_K_PHI_CORRELATION,
                "rationale": (
                    "A moderate positive coupling is frozen to avoid both an "
                    "independent-porosity extreme (rho=0) and a deterministic "
                    "porosity-from-K extreme (rho=1), while retaining independent "
                    "porosity structure for an unseen-realization test."
                ),
                "construction": [
                    "Standardize exact Z_K to zero mean / unit standard deviation.",
                    "Generate residual R from the frozen seed and covariance recipe.",
                    "Standardize R.",
                    "Orthogonalize R against Z_K over all 37,500 cells.",
                    "Re-standardize the orthogonal residual R_perp.",
                    "Set G_phi = 0.60*Z_K + sqrt(1-0.60^2)*R_perp.",
                ],
                "no_post_generation_correlation_retuning": True,
            },
            "bounded_porosity_transform": {
                "formula": "phi = 0.20 + 0.10 * tanh(G_phi / 2.0)",
                "center": PHI_CENTER,
                "half_range": PHI_HALF_RANGE,
                "open_lower_bound": PHI_MIN_OPEN,
                "open_upper_bound": PHI_MAX_OPEN,
                "clipping": False,
                "global_mean_rescaling": False,
                "global_pore_volume_rescaling": False,
                "per_realization_refit": False,
                "interpretation": (
                    "The bounded transform is symmetric around 0.20 in latent space. "
                    "Actual realization mean and total pore volume are outputs to report, "
                    "not quantities to force back to the AV1 constant-phi value."
                ),
            },
            "realization_policy": {
                "seed_registry_frozen_before_generation": True,
                "seed_pretesting": False,
                "realization_rejection": False,
                "reseeding": False,
                "visual_cherrypicking": False,
                "post_generation_parameter_tuning": False,
                "registry": REALIZATION_REGISTRY,
            },
            "fixed_controls": {
                "CO2_injection_tonnes_per_day": INJECTION_TPD,
                "producer_BHP_psi": PRODUCER_BHP_PSI,
                "target_days": CANONICAL_DAYS,
                "reason": (
                    "AV2 first isolates spatial porosity heterogeneity; "
                    "control-space expansion is not part of this experiment."
                ),
            },
        }

        adapter = {
            "protocol_id": PROTOCOL_ID,
            "face_porosity": {
                "rule": FACE_POROSITY_RULE,
                "formula": FACE_POROSITY_FORMULA,
                "permeability_weighting": False,
                "harmonic_averaging": False,
                "reason": (
                    "Porosity is a storage/pore-area fraction rather than a "
                    "transmissibility coefficient; use centered arithmetic "
                    "interpolation to internal Cartesian faces."
                ),
            },
            "pore_velocity": {
                "formula": "v_face = q_face / (A_face * phi_face)",
                "Darcy_flux_Q_reused_without_phi_scaling": True,
                "must_recompute_from_AV1_Q_and_AV2_phi": True,
            },
            "cell_pore_volume": {
                "formula": "PV_cell = phi_cell * V_bulk_cell",
                "cell_local": True,
                "global_PV_rescale": False,
            },
            "Pollock_and_TOF": {
                "AV1_trajectory_reuse_by_assumption": False,
                "retrace_required_in_A2": True,
                "terminal_TOF_recompute_required": True,
                "producer_capture_reaudit_required": True,
                "streamline_weight_reaudit_required": True,
            },
            "pressure_and_Darcy_expectation": {
                "direct_phi_dependency": False,
                "K_fluid_wells_unchanged": True,
                "A2_must_audit_invariance": True,
                "invariance_not_preclaimed_in_A1": True,
            },
            "mapback_and_capacity": {
                "R7D_terminal_halo_semantics_preserved": True,
                "AV1_exact_S0_H1_D1_cell_identity_preserved": False,
                "new_S0_from_AV2_streamlines": True,
                "new_H1_from_one_ring_same_layer_xy_face_neighbors_of_new_S0": True,
                "cell_capacity_uses_local_AV2_phi": True,
                "EOS_unchanged": True,
            },
        }

        split_firewall = {
            "protocol_id": PROTOCOL_ID,
            "split_unit": "complete porosity realization",
            "TRAIN": ["AV2PHI0001", "AV2PHI0002"],
            "VALIDATION": ["AV2PHI0003"],
            "LOCKED_OOD_TEST": ["AV2PHI0004"],
            "cell_level_random_split": False,
            "streamline_level_random_split_across_realizations": False,
            "locked_OOD_predictor_construction_allowed_before_open": True,
            "locked_OOD_target_access_before_checkpoint_freeze": False,
            "normalization_fit": "TRAIN realizations only",
            "checkpoint_selection": "TRAIN + VALIDATION only",
            "locked_OOD_evaluation": "one-touch after checkpoint freeze",
            "retraining_after_locked_OOD": False,
            "threshold_retuning_after_locked_OOD": False,
            "A5_A6_use_of_AV2PHI0004": (
                "Allowed only after the checkpoint and one-touch OOD result are frozen; "
                "no subsequent model or protocol tuning is permitted."
            ),
        }

        decision = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "protocol_id": PROTOCOL_ID,
            "field_generation_performed": False,
            "seed_pretesting_performed": False,
            "pressure_solve_performed": False,
            "Darcy_solve_performed": False,
            "Pollock_performed": False,
            "transport_generation_performed": False,
            "training_performed": False,
            "inference_performed": False,
            "mapback_performed": False,
            "CMG_validation_performed": False,
            "AV1_permeability_modified": False,
            "AV1_result_modified": False,
            "AV1E_external_validation_contract_modified": False,
            "A2_authorized": True,
            "next": {
                "milestone": "POSTV16-AV2-A2",
                "name": (
                    "Frozen Spatial-Porosity Realization Generation, "
                    "Pore-Velocity/Pollock/TOF Reconstruction, and Pressure-Q Invariance Audit"
                ),
                "authorized": True,
            },
        }

        summary = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "protocol_id": PROTOCOL_ID,
            "porosity_model_frozen": True,
            "porosity_bounds_open": [PHI_MIN_OPEN, PHI_MAX_OPEN],
            "porosity_transform": "0.20 + 0.10*tanh(G_phi/2.0)",
            "latent_K_phi_correlation": LATENT_K_PHI_CORRELATION,
            "porosity_realizations": len(REALIZATION_REGISTRY),
            "TRAIN_realizations": 2,
            "VALIDATION_realizations": 1,
            "LOCKED_OOD_realizations": 1,
            "AV1_K_unchanged": True,
            "global_porosity_rescale": False,
            "global_pore_volume_rescale": False,
            "face_porosity_rule": FACE_POROSITY_RULE,
            "field_generation": False,
            "training": False,
            "inference": False,
            "mapback": False,
            "CMG_validation": False,
            "next": decision["next"],
        }

        immutable_publish(
            out,
            {
                "PAD_Stream_POSTV16_AV2_A1_Summary.json": json_bytes(summary),
                "POSTV16_AV2_A1_Frozen_Spatial_Porosity_Field_Model.json": json_bytes(field_model),
                "POSTV16_AV2_A1_Frozen_Porosity_Realization_Registry.csv": csv_bytes(REALIZATION_REGISTRY),
                "POSTV16_AV2_A1_Frozen_Pore_Velocity_Pollock_Mapback_Adapter_Contract.json": json_bytes(adapter),
                "POSTV16_AV2_A1_Frozen_Train_Validation_LockedOOD_Firewall.json": json_bytes(split_firewall),
                "POSTV16_AV2_A1_Decision_Contract.json": json_bytes(decision),
                "POSTV16_AV2_A1_Final_Gate_Matrix.csv": csv_bytes(
                    [{"gate": k, **v} for k, v in gates.items()]
                ),
            },
        )

        manifest_rows = []
        for p in sorted(out.iterdir()):
            if p.is_file() and p.name != "POSTV16_AV2_A1_Artifact_Manifest.csv":
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
                "POSTV16_AV2_A1_Artifact_Manifest.csv": csv_bytes(manifest_rows)
            },
        )

        print("\n" + "=" * 196)
        print("POSTV16-AV2-A1: PASS")
        print("=" * 196)
        print(f"{'Status':116}: {STATUS_PASS}")
        print(f"{'AV1 permeability modified':116}: False")
        print(f"{'Porosity field generated':116}: False")
        print(f"{'Seed pretesting / rejection / reseeding':116}: False / False / False")
        print(f"{'Porosity transform':116}: phi = 0.20 + 0.10*tanh(G_phi/2.0)")
        print(f"{'Open porosity bounds':116}: (0.10, 0.30)")
        print(f"{'Latent K-phi correlation':116}: {LATENT_K_PHI_CORRELATION}")
        print(f"{'Residual continuity [major/minor/vertical ft]':116}: 200 / 200 / 15")
        print(f"{'Realizations TRAIN / VALIDATION / LOCKED_OOD':116}: 2 / 1 / 1")
        print(f"{'Face porosity rule':116}: arithmetic mean")
        print(f"{'Global phi/PV rescale':116}: False / False")
        print(f"{'Pressure/Darcy/Pollock/transport/training/inference/mapback':116}: False / False / False / False / False / False / False")
        print(f"{'CMG validation':116}: False")
        print(f"{'Next milestone authorized':116}: True")
        print(f"{'NEXT':116}: POSTV16-AV2-A2 — generate frozen phi realizations and reconstruct pore kinematics")
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
            "field_generation": False,
            "seed_pretesting": False,
            "training": False,
            "inference": False,
            "mapback": False,
            "CMG_validation": False,
            "AV1_result_changed": False,
            "AV1E_contract_changed": False,
            "next_milestone_authorized": False,
            "next_action": (
                "Audit only the AV2-A1 prospective field-model freeze. "
                "Do not generate or inspect any porosity realization until "
                "the A1 contract passes exactly."
            ),
        }

        data = json_bytes(report)
        p = blocked / "POSTV16_AV2_A1_Blocked_Report.json"

        if p.exists() and p.read_bytes() != data:
            suffix = hashlib.sha256(data).hexdigest()[:12]
            p = blocked / f"POSTV16_AV2_A1_Blocked_Report_{suffix}.json"

        if not p.exists():
            p.write_bytes(data)

        print("\n" + "=" * 196)
        print("POSTV16-AV2-A1: BLOCKED")
        print("=" * 196)
        print("Failed stage:", stage)
        print("Exception   :", repr(exc))
        print("Report      :", p)

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
