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

import numpy as np


MILESTONE = "POSTV16-AV3-A1"
PROTOCOL_ID = "POSTV16_AV3_A1_COREY_RELPERM_PARAMETER_FIELD_MODEL_CORRELATION_BOUNDS_SPLIT_REGISTRY_V1"

STATUS_PASS = (
    "AV3A1_COREY_RELPERM_PARAMETER_SUBSET_FIELD_MODEL_CORRELATION_BOUNDS_"
    "CHANNEL_SCHEMA_AND_SPLIT_REGISTRY_PROSPECTIVELY_FROZEN_NO_FIELD_GENERATION"
)

STATUS_BLOCKED = "AV3A1_COREY_RELPERM_FIELD_MODEL_FREEZE_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT_A0_COMMIT = "8fe1e386aada14b2c13acc8163acd63888d4a398"

A0 = "PAD_Stream_POSTV16_AV3_A0_Corey_Relperm_Authority_Gap_and_Physics_Impact_Freeze.py"
A0_BLOB = "a755a5ac20e81e81a925b39765bd303403b581b9"

AV2F_R1 = "PAD_Stream_POSTV16_AV2_F_R1_Technical_Key_Closure_and_Final_Outcome_Freeze.py"
AV2F_R1_BLOB = "562a298f5638bb16bc477fe2ddad81b780c4796d"

AV2A1 = "PAD_Stream_POSTV16_AV2_A1_Spatial_Porosity_Field_Model_and_Split_Registry_Freeze.py"
AV2A1_BLOB = "465d493cf6641c8929224d68a15e29aa38f9db69"

GAUSS = "SGSIM_50x50x15_GAUSS.csv"
GAUSS_BLOB = "56c87fed8b1e9fd7f6d3451be21a63659e6fa4bf"

SOURCE_BLOBS = {
    A0: A0_BLOB,
    AV2F_R1: AV2F_R1_BLOB,
    AV2A1: AV2A1_BLOB,
    GAUSS: GAUSS_BLOB,
}

BASE_AV3 = Path("post_v16") / RID / "POSTV16_AV3_Corey_Relperm_Heterogeneity"

A0_REL = BASE_AV3 / "POSTV16_AV3_A0_Corey_Relperm_Authority_Gap_and_Physics_Impact_Freeze"
A0_SUMMARY = "PAD_Stream_POSTV16_AV3_A0_Summary.json"
A0_GAP = "POSTV16_AV3_A0_Authority_Gap.json"
A0_SCOPE = "POSTV16_AV3_A0_Prospective_Scope_Contract.json"
A0_HANDOFF = "POSTV16_AV3_A0_A1_Handoff_Contract.json"
A0_DECISION = "POSTV16_AV3_A0_Decision_Contract.json"
A0_MANIFEST = "POSTV16_AV3_A0_Artifact_Manifest.csv"

A0_STATUS = (
    "AV3A0_SPATIAL_COREY_RELPERM_AUTHORITY_GAP_PHYSICS_IMPACT_AND_SCOPE_"
    "PROSPECTIVELY_FROZEN_NO_FIELD_GENERATION"
)

BASE_AV2 = Path("post_v16") / RID / "POSTV16_AV2_Variable_Porosity"
AV2F_REL = BASE_AV2 / "POSTV16_AV2_F_R1_Technical_Key_Closure_and_Final_Outcome_Freeze"
AV2F_SUMMARY = "PAD_Stream_POSTV16_AV2_F_R1_Summary.json"
AV2F_REGISTRY = "POSTV16_AV2_F_R1_Frozen_Realization_and_Domain_Registry.csv"
AV2F_MANIFEST = "POSTV16_AV2_F_R1_Artifact_Manifest.csv"

AV2F_STATUS = (
    "AV2_FINAL_VARIABLE_POROSITY_SCIENTIFIC_OUTCOME_FROZEN_"
    "AFTER_F_TECHNICAL_KEY_CLOSURE_AV3_A0_AUTHORIZED"
)

OUT_REL = BASE_AV3 / "POSTV16_AV3_A1_Corey_Relperm_Parameter_Field_Model_and_Split_Registry_Freeze"
BLOCK_REL = BASE_AV3 / "POSTV16_AV3_A1_BLOCKED"

# --------------------------------------------------------------------------------------------------
# Frozen AV3-A1 parameter subset.
# --------------------------------------------------------------------------------------------------

VARIABLE_PARAMETERS = ["nw", "no", "krw_max", "kro_max"]
FIXED_PARAMETERS = {
    "swc": 0.20,
    "sor": 0.20,
    "mu_w_cp": 0.50,
    "mu_o_cp": 5.00,
    "Pe_c": 22.0,
    "lambda_c": 2.0,
}

# Symmetric controlled perturbations around the exact AV2 constitutive authority.
PARAMETER_TRANSFORMS = {
    "nw": {
        "center": 3.0,
        "half_range": 1.0,
        "open_lower_bound": 2.0,
        "open_upper_bound": 4.0,
        "latent_scale": 2.0,
        "formula": "nw = 3.0 + 1.0*tanh(G_nw/2.0)",
    },
    "no": {
        "center": 3.0,
        "half_range": 1.0,
        "open_lower_bound": 2.0,
        "open_upper_bound": 4.0,
        "latent_scale": 2.0,
        "formula": "no = 3.0 + 1.0*tanh(G_no/2.0)",
    },
    "krw_max": {
        "center": 0.80,
        "half_range": 0.20,
        "open_lower_bound": 0.60,
        "open_upper_bound": 1.00,
        "latent_scale": 2.0,
        "formula": "krw_max = 0.80 + 0.20*tanh(G_krw/2.0)",
    },
    "kro_max": {
        "center": 0.80,
        "half_range": 0.20,
        "open_lower_bound": 0.60,
        "open_upper_bound": 1.00,
        "latent_scale": 2.0,
        "formula": "kro_max = 0.80 + 0.20*tanh(G_kro/2.0)",
    },
}

# Spatial structure: preserve the dissertation-base heterogeneity scale used by AV2.
GRID = [15, 50, 50]
DX_FT = 20.0
DY_FT = 20.0
DZ_FT = 4.0
MAJOR_RANGE_FT = 200.0
MINOR_RANGE_FT = 200.0
VERTICAL_RANGE_FT = 15.0
AZIMUTH_DEG = 30.0
COVARIANCE_MODEL = "exponential"
COVARIANCE_FORM = "C(h*) = exp(-3 h*)"
PERIODIC_MINIMUM_IMAGE = True

# Target LATENT cross-correlation. Order = nw,no,krw_max,kro_max.
TARGET_LATENT_CORRELATION = np.asarray(
    [
        [1.0, 0.5, 0.0, 0.0],
        [0.5, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.5],
        [0.0, 0.0, 0.5, 1.0],
    ],
    dtype=np.float64,
)

CURRENT_AV2_CHANNELS = [
    "xi",
    "pollock_tau_hat",
    "adv_tau_hat",
    "log10_Kh",
    "log10_Kz_over_Kh",
    "porosity",
    "pressure_z",
    "target_time_hat",
    "target_eta_sequence",
]

NEW_AV3_CHANNELS = [
    "nw_hat",
    "no_hat",
    "krw_max_hat",
    "kro_max_hat",
]

AV3_CHANNELS = CURRENT_AV2_CHANNELS + NEW_AV3_CHANNELS

# AV3 uses the exact same split identities as the paired frozen AV2 porosity base.
REALIZATION_REGISTRY = [
    {
        "corey_realization_id": "AV3CR0001",
        "base_seed": 260301,
        "paired_porosity_realization_id": "AV2PHI0001",
        "partition": "TRAIN",
        "locked_until": "N/A",
    },
    {
        "corey_realization_id": "AV3CR0002",
        "base_seed": 260302,
        "paired_porosity_realization_id": "AV2PHI0002",
        "partition": "TRAIN",
        "locked_until": "N/A",
    },
    {
        "corey_realization_id": "AV3CR0003",
        "base_seed": 260303,
        "paired_porosity_realization_id": "AV2PHI0003",
        "partition": "VALIDATION",
        "locked_until": "N/A",
    },
    {
        "corey_realization_id": "AV3CR0004",
        "base_seed": 260304,
        "paired_porosity_realization_id": "AV2PHI0004",
        "partition": "LOCKED_OOD_TEST",
        "locked_until": "AV3 checkpoint frozen after TRAIN/VALIDATION selection",
    },
]

CANONICAL_DAYS = [30.0, 60.0, 100.0, 150.0, 250.0, 365.0, 500.0, 750.0, 1000.0]


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
    rr = read_csv(directory / name)
    m = {r["file"]: r["sha256"] for r in rr}
    if not m:
        raise GateError("manifest_empty:" + name)
    for fn, expected in m.items():
        p = directory / fn
        if not p.is_file():
            raise GateError("manifest_missing:" + fn)
        if sha256_file(p) != expected:
            raise GateError("manifest_SHA:" + fn)
    return m


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


def self_test() -> None:
    ids = [r["corey_realization_id"] for r in REALIZATION_REGISTRY]
    seeds = [r["base_seed"] for r in REALIZATION_REGISTRY]
    paired = [r["paired_porosity_realization_id"] for r in REALIZATION_REGISTRY]
    parts = [r["partition"] for r in REALIZATION_REGISTRY]

    assert len(ids) == len(set(ids)) == 4
    assert len(seeds) == len(set(seeds)) == 4
    assert paired == ["AV2PHI0001", "AV2PHI0002", "AV2PHI0003", "AV2PHI0004"]
    assert parts.count("TRAIN") == 2
    assert parts.count("VALIDATION") == 1
    assert parts.count("LOCKED_OOD_TEST") == 1

    ev = np.linalg.eigvalsh(TARGET_LATENT_CORRELATION)
    assert np.min(ev) > 0.0

    for name, d in PARAMETER_TRANSFORMS.items():
        for g in (-6.0, -2.0, 0.0, 2.0, 6.0):
            v = d["center"] + d["half_range"] * math.tanh(g / d["latent_scale"])
            assert d["open_lower_bound"] < v < d["open_upper_bound"], (name, g, v)

    assert PARAMETER_TRANSFORMS["nw"]["open_lower_bound"] == 2.0
    assert PARAMETER_TRANSFORMS["nw"]["open_upper_bound"] == 4.0
    assert PARAMETER_TRANSFORMS["nw"]["center"] == 3.0
    assert PARAMETER_TRANSFORMS["no"]["open_lower_bound"] == 2.0
    assert PARAMETER_TRANSFORMS["no"]["open_upper_bound"] == 4.0
    assert PARAMETER_TRANSFORMS["no"]["center"] == 3.0
    assert FIXED_PARAMETERS["swc"] == 0.20
    assert FIXED_PARAMETERS["sor"] == 0.20
    assert len(AV3_CHANNELS) == 13

    print("POSTV16-AV3-A1 Corey/relperm field-model freeze self-test: PASS")


def main(root: Path, drive: Path) -> int:
    gates: dict[str, dict[str, Any]] = {}
    stage = "preflight"

    out = drive / OUT_REL
    blocked = drive / BLOCK_REL

    def gate(name: str, passed: Any, value: Any = None) -> None:
        ok = bool(passed)
        gates[name] = {"passed": ok, "value": value}
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {value}" if value is not None else ""))
        if not ok:
            raise GateError(name)

    print("=" * 200)
    print("POSTV16-AV3-A1 — COREY / RELPERM PARAMETER-SUBSET + FIELD-MODEL + CORRELATION + BOUNDS + SPLIT-REGISTRY FREEZE")
    print("=" * 200)
    print("PROSPECTIVE DESIGN/FREEZE ONLY.")
    print("NO COREY/RELPERM FIELD GENERATION. NO SEED PRETESTING. NO REJECTION OR RESEEDING.")
    print("NO TEACHER GENERATION. NO TRAINING. NO INFERENCE. NO PRESSURE RE-SOLVE. NO POLLOCK RETRACE.")
    print("NO MAPBACK. NO LP. NO CMG.")
    print("Swc=Sor=0.20 REMAIN FIXED; AV2 SATURATION/CAPACITY SEMANTICS ARE PRESERVED.")
    print()

    try:
        root = root.resolve()
        drive = drive.resolve()

        stage = "repository_authority"
        parent = git_text(root, "rev-parse", "HEAD^")
        status = git_text(root, "status", "--porcelain")

        gate("repository_parent_is_AV3A0_commit", parent == PARENT_A0_COMMIT, parent)
        gate("repository_clean", status == "", repr(status))

        for fn, expected in SOURCE_BLOBS.items():
            p = root / fn
            actual = git_blob(p, root) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact", actual == expected, actual)

        # ------------------------------------------------------------------------------------------
        # Bind exact A0 PASS and A1 authorization.
        # ------------------------------------------------------------------------------------------
        stage = "AV3A0_binding"
        a0 = drive / A0_REL
        gate("AV3A0_output_present", a0.is_dir(), str(a0))

        m0 = verify_manifest(a0, A0_MANIFEST)
        gate("AV3A0_manifest_SHA_closure", len(m0) == 8, len(m0))

        s0 = load_json(a0 / A0_SUMMARY)
        gap0 = load_json(a0 / A0_GAP)
        scope0 = load_json(a0 / A0_SCOPE)
        h0 = load_json(a0 / A0_HANDOFF)
        d0 = load_json(a0 / A0_DECISION)

        gate("AV3A0_status_exact", s0["status"] == A0_STATUS, s0["status"])
        gate("AV3A0_parameter_subset_not_selected", s0["parameter_subset_selected"] is False)
        gate("AV3A0_no_field_generation", s0["field_generation"] is False)
        gate("AV3A0_A1_authorized", s0["AV3_A1_authorized"] is True)
        gate("AV3A0_A1_next_id_exact", h0["milestone"] == "POSTV16-AV3-A1")
        gate("AV3A0_A1_execution_false", h0["execution"] is False)
        gate("AV3A0_pressure_Q_reuse",
             d0["pressure_Q_reuse_authorized_within_AV3_transport_only_scope"] is True)
        gate("AV3A0_Pollock_TOF_reuse",
             d0["AV2_Pollock_TOF_reuse_authorized_within_AV3_transport_only_scope"] is True)
        gate("AV3A0_R7D_geometry_reuse",
             d0["AV2_R7D_graph_geometry_reuse_authorized_within_AV3_transport_only_scope"] is True)
        gate("AV3A0_swc_sor_special_semantics_if_varied",
             d0["swc_sor_variation_requires_explicit_A1_semantics"] is True)

        # ------------------------------------------------------------------------------------------
        # Bind frozen AV2 realization registry used as the AV3 geological base.
        # ------------------------------------------------------------------------------------------
        stage = "AV2_base_registry_binding"
        av2f = drive / AV2F_REL
        gate("AV2F_R1_output_present", av2f.is_dir(), str(av2f))

        mf = verify_manifest(av2f, AV2F_MANIFEST)
        gate("AV2F_R1_manifest_SHA_closure", len(mf) == 8, len(mf))

        sf = load_json(av2f / AV2F_SUMMARY)
        gate("AV2F_R1_status_exact", sf["status"] == AV2F_STATUS, sf["status"])

        av2_registry = read_csv(av2f / AV2F_REGISTRY)
        av2_pairs = [
            (r["porosity_realization_id"], r["partition"])
            for r in av2_registry
        ]

        expected_av2_pairs = [
            ("AV2PHI0001", "TRAIN"),
            ("AV2PHI0002", "TRAIN"),
            ("AV2PHI0003", "VALIDATION"),
            ("AV2PHI0004", "LOCKED_OOD_TEST"),
        ]

        gate("AV2_registry_exact_for_AV3_pairing", av2_pairs == expected_av2_pairs, av2_pairs)

        # ------------------------------------------------------------------------------------------
        # Prospective parameter-subset decision.
        # ------------------------------------------------------------------------------------------
        stage = "parameter_subset_freeze"

        gate("variable_parameter_subset_exact",
             VARIABLE_PARAMETERS == ["nw", "no", "krw_max", "kro_max"],
             VARIABLE_PARAMETERS)

        gate("swc_fixed_0p20", FIXED_PARAMETERS["swc"] == 0.20)
        gate("sor_fixed_0p20", FIXED_PARAMETERS["sor"] == 0.20)

        gate("AV2_saturation_lower_bound_preserved",
             FIXED_PARAMETERS["swc"] == 0.20)
        gate("AV2_saturation_upper_bound_preserved",
             1.0 - FIXED_PARAMETERS["sor"] == 0.80)

        # Open bounded parameter transforms.
        for name, d in PARAMETER_TRANSFORMS.items():
            if name in {"nw", "no"}:
                gate(
                    f"{name}_range_2_to_4",
                    d["open_lower_bound"] == 2.0
                    and d["center"] == 3.0
                    and d["open_upper_bound"] == 4.0,
                    [d["open_lower_bound"], d["center"], d["open_upper_bound"]],
                )
                gate(
                    f"{name}_AV2_baseline_is_lower_endpoint",
                    d["open_lower_bound"] == 2.0,
                    2.0,
                )
            else:
                gate(
                    f"{name}_center_matches_AV2",
                    d["center"] == 0.80,
                    d["center"],
                )
            gate(f"{name}_open_bounds_ordered",
                 0.0 < d["open_lower_bound"] < d["center"] < d["open_upper_bound"],
                 [d["open_lower_bound"], d["center"], d["open_upper_bound"]])
            if name in {"krw_max", "kro_max"}:
                gate(f"{name}_physical_endpoint_le_1", d["open_upper_bound"] <= 1.0)

        # ------------------------------------------------------------------------------------------
        # Latent correlation and independence design.
        # ------------------------------------------------------------------------------------------
        stage = "correlation_freeze"

        eig = np.linalg.eigvalsh(TARGET_LATENT_CORRELATION)
        gate("latent_correlation_symmetric",
             np.allclose(TARGET_LATENT_CORRELATION, TARGET_LATENT_CORRELATION.T))
        gate("latent_correlation_unit_diagonal",
             np.allclose(np.diag(TARGET_LATENT_CORRELATION), np.ones(4)))
        gate("latent_correlation_positive_definite",
             float(np.min(eig)) > 0.0,
             eig.tolist())
        gate("nw_no_latent_correlation_0p5",
             TARGET_LATENT_CORRELATION[0, 1] == 0.5)
        gate("krw_kro_latent_correlation_0p5",
             TARGET_LATENT_CORRELATION[2, 3] == 0.5)
        gate("exponent_endpoint_latent_cross_correlation_zero",
             np.allclose(TARGET_LATENT_CORRELATION[:2, 2:], 0.0))

        # ------------------------------------------------------------------------------------------
        # Split registry.
        # ------------------------------------------------------------------------------------------
        stage = "split_registry_freeze"

        ids = [r["corey_realization_id"] for r in REALIZATION_REGISTRY]
        seeds = [r["base_seed"] for r in REALIZATION_REGISTRY]
        paired = [r["paired_porosity_realization_id"] for r in REALIZATION_REGISTRY]
        parts = [r["partition"] for r in REALIZATION_REGISTRY]

        gate("AV3_realization_ids_unique", len(ids) == len(set(ids)) == 4, ids)
        gate("AV3_base_seeds_unique", len(seeds) == len(set(seeds)) == 4, seeds)
        gate("AV3_exact_2_train_1_val_1_OOD",
             parts.count("TRAIN") == 2
             and parts.count("VALIDATION") == 1
             and parts.count("LOCKED_OOD_TEST") == 1,
             parts)
        gate("AV3_pairing_matches_AV2_registry",
             paired == [x[0] for x in expected_av2_pairs],
             paired)

        # ------------------------------------------------------------------------------------------
        # New conditioning schema.
        # ------------------------------------------------------------------------------------------
        stage = "channel_schema_freeze"

        gate("AV2_channel_prefix_exact_9", len(CURRENT_AV2_CHANNELS) == 9)
        gate("AV3_new_channel_count_4", len(NEW_AV3_CHANNELS) == 4)
        gate("AV3_total_channel_count_13", len(AV3_CHANNELS) == 13)
        gate("AV3_preserves_AV2_9_channel_prefix",
             AV3_CHANNELS[:9] == CURRENT_AV2_CHANNELS)
        gate("AV3_appends_constitutive_channels",
             AV3_CHANNELS[9:] == NEW_AV3_CHANNELS)

        # ------------------------------------------------------------------------------------------
        # Freeze exact prospective contracts.
        # ------------------------------------------------------------------------------------------
        field_contract = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "protocol_id": PROTOCOL_ID,
            "role": (
                "Prospective synthetic AV3 spatial Corey/relative-permeability field design. "
                "The exponent range is anchored to the frozen AV2 value 2.0 as its lower endpoint, "
                "while endpoint-permeability fields remain centered on the AV2 value 0.80. "
                "This is not represented as laboratory-calibrated rock-function data."
            ),
            "variable_parameters": VARIABLE_PARAMETERS,
            "fixed_parameters": FIXED_PARAMETERS,
            "parameter_transforms": PARAMETER_TRANSFORMS,
            "saturation_semantics": {
                "Swc": 0.20,
                "Sor": 0.20,
                "admissible_transport_saturation_interval": [0.20, 0.80],
                "incremental_CO2_saturation_capacity": 0.60,
                "AV2_local_pore_volume_capacity_rule_preserved": True,
                "reason": (
                    "A1 deliberately keeps Swc/Sor fixed so AV3 isolates spatial relperm/Corey "
                    "shape heterogeneity without simultaneously redesigning saturation bounds "
                    "or the AV2 grid-capacity authority."
                ),
            },
            "spatial_covariance": {
                "type": "deterministic_periodic_spectral_Gaussian_random_field",
                "covariance_model": COVARIANCE_MODEL,
                "covariance_form": COVARIANCE_FORM,
                "major_range_ft": MAJOR_RANGE_FT,
                "minor_range_ft": MINOR_RANGE_FT,
                "vertical_range_ft": VERTICAL_RANGE_FT,
                "azimuth_deg": AZIMUTH_DEG,
                "periodic_minimum_image": PERIODIC_MINIMUM_IMAGE,
                "grid_kji": GRID,
                "cell_ft": [DZ_FT, DY_FT, DX_FT],
            },
            "latent_independence_from_AV2_geology": {
                "target": "zero sample inner product before bounded transform",
                "orthogonalize_against": [
                    "standardized exact SGSim Gaussian permeability latent Z_K",
                    "standardized paired AV2 porosity latent Z_phi reconstructed from phi",
                ],
                "paired_phi_inverse_transform": (
                    "G_phi = 2*atanh((phi-0.20)/0.10), followed by standardization"
                ),
                "basis_rule": (
                    "Orthonormalize Z_K and Z_phi first. For each raw constitutive residual, "
                    "remove projections onto both geology basis vectors and all previously "
                    "accepted constitutive residual basis vectors; then standardize."
                ),
                "physical_field_Pearson_independence_claim": False,
                "reason": (
                    "The nonlinear bounded transform can alter physical-space Pearson "
                    "correlation. A2 must report physical correlations as outcomes; no "
                    "post-generation retuning is allowed."
                ),
            },
            "latent_cross_parameter_correlation": {
                "parameter_order": VARIABLE_PARAMETERS,
                "matrix": TARGET_LATENT_CORRELATION.tolist(),
                "construction": (
                    "Apply the Cholesky factor of the frozen 4x4 target matrix to the "
                    "orthonormal constitutive residual basis."
                ),
                "nw_no_target": 0.5,
                "krwmax_kromax_target": 0.5,
                "exponent_endpoint_target": 0.0,
            },
            "seed_policy": {
                "registry_frozen_before_generation": True,
                "base_seed_registry": REALIZATION_REGISTRY,
                "component_seed_formula": (
                    "component_seed = 10*base_seed + component_index, "
                    "with component_index 1:nw, 2:no, 3:krw_max, 4:kro_max"
                ),
                "seed_pretesting": False,
                "realization_rejection": False,
                "reseeding": False,
                "visual_cherrypicking": False,
                "post_generation_parameter_retuning": False,
            },
            "AV3_transport_only_firewall": {
                "pressure_Q_reused_from_AV2": True,
                "Pollock_TOF_reused_from_AV2": True,
                "R7D_graph_geometry_reused_from_AV2": True,
                "pressure_resolve": False,
                "Pollock_retrace": False,
                "relperm_total_mobility_pressure_feedback": "DEFERRED_TO_AV4",
            },
        }

        channel_contract = {
            "protocol_id": PROTOCOL_ID,
            "existing_AV2_channels_preserved_in_order": CURRENT_AV2_CHANNELS,
            "new_AV3_channels_appended": NEW_AV3_CHANNELS,
            "AV3_total_channel_count": 13,
            "new_channel_scaling": {
                "nw_hat": "(nw - 3.0) / 1.0",
                "no_hat": "(no - 3.0) / 1.0",
                "krw_max_hat": "(krw_max - 0.80) / 0.20",
                "kro_max_hat": "(kro_max - 0.80) / 0.20",
                "range": "analytically open-bounded in (-1,1)",
                "fit_to_training_data": False,
                "uses_validation_statistics": False,
                "uses_locked_OOD_statistics": False,
            },
            "sampling_rule_for_A2": (
                "Trilinearly sample each cell-centered constitutive field to the exact "
                "paired AV2 201-node Pollock coordinates. No streamline retracing."
            ),
            "AV2_checkpoint_compatibility": {
                "epoch198_checkpoint_input_width": 9,
                "AV3_required_input_width": 13,
                "checkpoint_direct_reuse_as_AV3_model": False,
                "checkpoint_retained_as_historical_baseline": True,
            },
        }

        split_contract = {
            "protocol_id": PROTOCOL_ID,
            "registry": REALIZATION_REGISTRY,
            "split_counts": {
                "TRAIN": 2,
                "VALIDATION": 1,
                "LOCKED_OOD_TEST": 1,
            },
            "AV3_locked_OOD_semantics": (
                "AV3CR0004 is locked with respect to all AV3 transport targets and AV3 "
                "model selection. Its paired AV2 porosity realization is historical AV2 "
                "evidence, but no AV3 teacher target may be generated/opened before the "
                "AV3 checkpoint is frozen."
            ),
            "normalization_rule": (
                "Existing AV2 channel normalizations remain frozen because pressure/Q, "
                "geometry, K, phi, and split pairing are unchanged. New constitutive "
                "channels use analytical fixed scaling and require no fitted statistics."
            ),
        }

        a2_handoff = {
            "milestone": "POSTV16-AV3-A2",
            "name": (
                "Spatial Corey / Relative-Permeability Field Realization, "
                "Certification, and Frozen-Streamline Sampling Execution"
            ),
            "authorized": True,
            "execution": True,
            "required_work": [
                "generate all four frozen AV3 constitutive realizations from the exact seed registry",
                "do not reject, reseed, or tune any realization",
                "certify all four cell-centered fields remain inside frozen open bounds",
                "certify latent geology orthogonality and frozen cross-parameter covariance",
                "report physical-space K/phi/parameter correlations without retuning",
                "pair each AV3 realization with its exact frozen AV2 porosity/kinematic realization",
                "trilinearly sample nw,no,krw_max,kro_max to the 201-node AV2 Pollock coordinates",
                "preserve pressure/Q, Pollock paths, TOF, S0/H1/D1 graph geometry, Swc/Sor, and grid capacity",
                "do not generate transport Y targets",
                "do not train or infer any neural network",
            ],
        }

        decision = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "protocol_id": PROTOCOL_ID,
            "selected_spatial_parameters": VARIABLE_PARAMETERS,
            "swc_spatially_variable": False,
            "sor_spatially_variable": False,
            "AV2_saturation_bounds_preserved": True,
            "AV2_grid_capacity_semantics_preserved": True,
            "latent_independence_from_K_and_phi_frozen": True,
            "latent_cross_parameter_correlation_frozen": True,
            "split_registry_frozen": True,
            "new_predictor_channel_schema_frozen": True,
            "AV3_input_channels": 13,
            "AV2_checkpoint_directly_usable_as_AV3_checkpoint": False,
            "pressure_Q_reuse": True,
            "Pollock_TOF_reuse": True,
            "R7D_graph_geometry_reuse": True,
            "field_generation_performed": False,
            "teacher_generation_performed": False,
            "training_performed": False,
            "inference_performed": False,
            "pressure_resolve_performed": False,
            "Pollock_retrace_performed": False,
            "mapback_performed": False,
            "LP_execution_performed": False,
            "CMG_validation_performed": False,
            "AV3_A2_authorized": True,
            "next": a2_handoff,
        }

        summary = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "protocol_id": PROTOCOL_ID,
            "variable_parameter_count": 4,
            "fixed_swc": 0.20,
            "fixed_sor": 0.20,
            "AV3_input_channels": 13,
            "realization_count": 4,
            "TRAIN_realizations": 2,
            "VALIDATION_realizations": 1,
            "LOCKED_OOD_realizations": 1,
            "field_generation": False,
            "teacher_generation": False,
            "training": False,
            "inference": False,
            "pressure_resolve": False,
            "Pollock_retrace": False,
            "mapback": False,
            "LP_execution": False,
            "CMG_validation": False,
            "AV3_A2_authorized": True,
            "next": a2_handoff,
        }

        files = {
            "PAD_Stream_POSTV16_AV3_A1_Summary.json": json_bytes(summary),
            "POSTV16_AV3_A1_Selected_Parameter_Subset_and_Bounds.json": json_bytes({
                "variable_parameters": VARIABLE_PARAMETERS,
                "fixed_parameters": FIXED_PARAMETERS,
                "parameter_transforms": PARAMETER_TRANSFORMS,
            }),
            "POSTV16_AV3_A1_Field_Model_and_Correlation_Contract.json": json_bytes(field_contract),
            "POSTV16_AV3_A1_Frozen_Corey_Relperm_Realization_Registry.csv": csv_bytes(REALIZATION_REGISTRY),
            "POSTV16_AV3_A1_Predictor_Channel_Contract.json": json_bytes(channel_contract),
            "POSTV16_AV3_A1_Split_and_Leakage_Firewall.json": json_bytes(split_contract),
            "POSTV16_AV3_A1_A2_Handoff_Contract.json": json_bytes(a2_handoff),
            "POSTV16_AV3_A1_Decision_Contract.json": json_bytes(decision),
            "POSTV16_AV3_A1_Final_Gate_Matrix.csv": csv_bytes(
                [{"gate": k, **v} for k, v in gates.items()]
            ),
        }

        immutable_publish(out, files)

        manifest_rows = []
        for q in sorted(out.iterdir()):
            if q.is_file() and q.name != "POSTV16_AV3_A1_Artifact_Manifest.csv":
                manifest_rows.append({
                    "file": q.name,
                    "sha256": sha256_file(q),
                    "bytes": q.stat().st_size,
                })

        immutable_publish(
            out,
            {"POSTV16_AV3_A1_Artifact_Manifest.csv": csv_bytes(manifest_rows)},
        )

        print()
        print("=" * 200)
        print("POSTV16-AV3-A1: FULL PARAMETER / FIELD-MODEL / SPLIT FREEZE PASS")
        print("=" * 200)
        print("Spatially variable parameters             : nw, no, krw_max, kro_max")
        print("Swc / Sor                                 : 0.20 / 0.20 FIXED")
        print("nw / no open bounds                       : (2.0, 4.0)")
        print("krw_max / kro_max open bounds             : (0.60, 1.00)")
        print("Latent independence from K / phi          : FROZEN")
        print("Latent corr(nw,no)                         : 0.50")
        print("Latent corr(krw_max,kro_max)               : 0.50")
        print("Exponent-endpoint latent cross-correlation : 0.00")
        print("Realizations / split                      : 4 = 2 TRAIN + 1 VAL + 1 LOCKED OOD")
        print("AV2 channels / AV3 channels               : 9 / 13")
        print("AV2 saturation bounds / capacity           : PRESERVED")
        print("Pressure/Q / Pollock/TOF                  : REUSED FROM AV2")
        print("Field generation                           : False")
        print("POSTV16-AV3-A2                             : AUTHORIZED")
        print("=" * 200)
        return 0

    except Exception as exc:
        blocked.mkdir(parents=True, exist_ok=True)
        report = {
            "milestone": MILESTONE,
            "status": STATUS_BLOCKED,
            "failed_stage": stage,
            "exception": repr(exc),
            "gates": gates,
            "field_generation_performed": False,
            "teacher_generation_performed": False,
            "training_performed": False,
            "inference_performed": False,
            "pressure_resolve_performed": False,
            "Pollock_retrace_performed": False,
            "mapback_performed": False,
            "LP_execution_performed": False,
            "CMG_validation_performed": False,
            "AV3_A2_authorized": False,
        }
        q = blocked / "POSTV16_AV3_A1_Blocked_Report.json"
        if not q.exists():
            q.write_bytes(json_bytes(report))
        print("POSTV16-AV3-A1: BLOCKED", stage, repr(exc))
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
