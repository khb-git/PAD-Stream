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

MILESTONE = "POSTV16-AV3-A0"
PROTOCOL_ID = "POSTV16_AV3_A0_SPATIAL_COREY_RELPERM_AUTHORITY_GAP_AND_PHYSICS_IMPACT_FREEZE_V1"
STATUS_PASS = "AV3A0_SPATIAL_COREY_RELPERM_AUTHORITY_GAP_PHYSICS_IMPACT_AND_SCOPE_PROSPECTIVELY_FROZEN_NO_FIELD_GENERATION"
STATUS_BLOCKED = "AV3A0_TECHNICAL_FREEZE_BLOCKED"

RID = "PAD_STREAM_V16_RC1_B92D52088D01078A"
PARENT_AV2_FINAL = "c888e180099ecad3f24287c6a7f99468e57dd2ab"
CKSHA = "1c82867c53d9d3a63ee8ba9dab5ab65e9bdfaf6330fb5239954d02d7f566ef28"

# Exact source lineage used only as read-only scientific authority.
AV2F_R1 = "PAD_Stream_POSTV16_AV2_F_R1_Technical_Key_Closure_and_Final_Outcome_Freeze.py"
AV2F_R1_BLOB = "562a298f5638bb16bc477fe2ddad81b780c4796d"
AV2A3 = "PAD_Stream_POSTV16_AV2_A3_Variable_Porosity_Teacher_Dataset_and_PIRNN_Protocol.py"
AV2A3_BLOB = "9b209abc3a2abb905b9250a16344e52160e61c47"
C7 = "PAD_Stream_V16C7_Pollock_TOF_Full_BL_CCUS_Transport_Adapter_Physics_Contract.py"
C7_BLOB = "78b312ad16c1778a62cfbd9a77a9793aa14044d4"
C25 = "PAD_Stream_V16C25_Differentiable_Pollock_Full_Physics_Residual_Boundary_Mask_and_Physics_Loss_Weight_Authority_Contract.py"
C25_BLOB = "0a4740b95c2b5e5d15db3137414e663e1e9b6282"
C26 = "PAD_Stream_V16C26_EXP2_Physics_Informed_Training_Execution_Best_Validation_Checkpoint_and_Locked_Test_Evaluation.py"
C26_BLOB = "62e19e6b502fb3ab101a2589251c26b5f9ad9031"
STAGE4 = "pi_rnn_stage4_full_godunov.py"
STAGE4_BLOB = "0c276317a5d8487c190c7185908b228544c33073"

SOURCE_BLOBS = {
    AV2F_R1: AV2F_R1_BLOB,
    AV2A3: AV2A3_BLOB,
    C7: C7_BLOB,
    C25: C25_BLOB,
    C26: C26_BLOB,
    STAGE4: STAGE4_BLOB,
}

BASE_AV2 = Path("post_v16") / RID / "POSTV16_AV2_Variable_Porosity"
AV2F_R1_REL = BASE_AV2 / "POSTV16_AV2_F_R1_Technical_Key_Closure_and_Final_Outcome_Freeze"
AV2F_R1_SUMMARY = "PAD_Stream_POSTV16_AV2_F_R1_Summary.json"
AV2F_R1_DECISION = "POSTV16_AV2_F_R1_Decision_Contract.json"
AV2F_R1_HANDOFF = "POSTV16_AV2_F_R1_AV3_Handoff_Contract.json"
AV2F_R1_MANIFEST = "POSTV16_AV2_F_R1_Artifact_Manifest.csv"

AV2F_R1_STATUS = (
    "AV2_FINAL_VARIABLE_POROSITY_SCIENTIFIC_OUTCOME_FROZEN_"
    "AFTER_F_TECHNICAL_KEY_CLOSURE_AV3_A0_AUTHORIZED"
)

BASE_AV3 = Path("post_v16") / RID / "POSTV16_AV3_Corey_Relperm_Heterogeneity"
OUT_REL = BASE_AV3 / "POSTV16_AV3_A0_Corey_Relperm_Authority_Gap_and_Physics_Impact_Freeze"
BLOCK_REL = BASE_AV3 / "POSTV16_AV3_A0_BLOCKED"

# Frozen AV2 constitutive vector.
AV2_CONST = {
    "nw": 2.0,
    "no": 2.0,
    "swc": 0.2,
    "sor": 0.2,
    "krw_max": 0.8,
    "kro_max": 0.8,
    "mu_w_cp": 0.5,
    "mu_o_cp": 5.0,
    "Pe_c": 22.0,
    "lambda_c": 2.0,
}

CURRENT_CHANNELS = [
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

CANDIDATE_SPATIAL_PARAMETERS = [
    "nw",
    "no",
    "krw_max",
    "kro_max",
    "swc",
    "sor",
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
    m = {r["file"]: r["sha256"] for r in rows}
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
        for k in row:
            if k not in fields:
                fields.append(k)
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


def require_markers(text: str, markers: list[str], label: str) -> None:
    missing = [m for m in markers if m not in text]
    if missing:
        raise GateError(f"{label}_missing_markers:{missing}")


def self_test() -> None:
    assert len(CURRENT_CHANNELS) == 9
    assert CANDIDATE_SPATIAL_PARAMETERS == [
        "nw", "no", "krw_max", "kro_max", "swc", "sor"
    ]
    assert AV2_CONST["swc"] == 0.2 and AV2_CONST["sor"] == 0.2
    print("POSTV16-AV3-A0 Corey/relperm authority-gap freeze self-test: PASS")


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

    print("=" * 198)
    print("POSTV16-AV3-A0 — SPATIAL COREY / RELATIVE-PERMEABILITY AUTHORITY-GAP AND PHYSICS-IMPACT FREEZE")
    print("=" * 198)
    print("DESIGN / FREEZE ONLY.")
    print("NO RELPERM FIELD GENERATION. NO TEACHER GENERATION. NO TRAINING. NO INFERENCE.")
    print("NO PRESSURE RE-SOLVE. NO POLLOCK RETRACE. NO MAPBACK. NO LP. NO CMG.")
    print("NO AV3 PARAMETER DISTRIBUTION OR PARAMETER SUBSET IS CHOSEN IN A0.")
    print()

    try:
        root = root.resolve()
        drive = drive.resolve()

        stage = "repository_authority"
        parent = git_text(root, "rev-parse", "HEAD^")
        status = git_text(root, "status", "--porcelain")

        gate("repository_parent_is_AV2_final_commit", parent == PARENT_AV2_FINAL, parent)
        gate("repository_clean", status == "", repr(status))

        for fn, expected in SOURCE_BLOBS.items():
            p = root / fn
            actual = git_blob(p, root) if p.is_file() else "missing"
            gate(f"{Path(fn).stem}_git_blob_exact", actual == expected, actual)

        stage = "AV2_final_binding"
        av2f = drive / AV2F_R1_REL
        gate("AV2F_R1_output_present", av2f.is_dir(), str(av2f))
        m = verify_manifest(av2f, AV2F_R1_MANIFEST)
        gate("AV2F_R1_manifest_SHA_closure", len(m) == 8, len(m))

        s = load_json(av2f / AV2F_R1_SUMMARY)
        d = load_json(av2f / AV2F_R1_DECISION)
        h = load_json(av2f / AV2F_R1_HANDOFF)

        gate("AV2F_R1_status_exact", s["status"] == AV2F_R1_STATUS, s["status"])
        gate("AV2_scientific_outcome_frozen", d["AV2_scientific_outcome_frozen"] is True)
        gate("AV2_checkpoint_SHA_exact", d["checkpoint_sha256"] == CKSHA, d["checkpoint_sha256"])
        gate("AV3_A0_authorized", d["AV3_A0_authorized"] is True)
        gate("AV3_A0_next_id_exact", d["next"]["milestone"] == "POSTV16-AV3-A0")
        gate("AV3_execution_not_authorized", d["next"]["execution"] is False)
        gate("AV2_checkpoint_not_automatically_authoritative_for_AV3",
             h["AV3_initial_scope"]["AV2_checkpoint_may_be_assumed_authoritative_for_AV3"] is False)

        stage = "constitutive_source_audit"
        a3_text = (root / AV2A3).read_text(encoding="utf-8")

        require_markers(
            a3_text,
            [
                '"nw": 2.0',
                '"no": 2.0',
                '"swc": 0.2',
                '"sor": 0.2',
                '"krw_max": 0.8',
                '"kro_max": 0.8',
                '"mu_w": 0.5',
                '"mu_o": 5.0',
                "INPUT_CHANNELS = 9",
                "def relperm(",
                "def fw(",
                "def dshape(",
                "def advective_step(",
                "def capillary_implicit_local_phi(",
                "X7 = np.stack(",
                "X9 = np.concatenate(",
            ],
            "AV2A3",
        )
        gate("AV2A3_constitutive_markers_exact", True)

        # Current frozen authority is constant in space.
        gate("AV2_nw_constant_2", AV2_CONST["nw"] == 2.0)
        gate("AV2_no_constant_2", AV2_CONST["no"] == 2.0)
        gate("AV2_swc_constant_0p2", AV2_CONST["swc"] == 0.2)
        gate("AV2_sor_constant_0p2", AV2_CONST["sor"] == 0.2)
        gate("AV2_krwmax_constant_0p8", AV2_CONST["krw_max"] == 0.8)
        gate("AV2_kromax_constant_0p8", AV2_CONST["kro_max"] == 0.8)
        gate("AV2_input_channel_count_9", len(CURRENT_CHANNELS) == 9, len(CURRENT_CHANNELS))

        # No current input channel explicitly carries any Corey/relperm parameter.
        overlap = sorted(set(CURRENT_CHANNELS).intersection(CANDIDATE_SPATIAL_PARAMETERS))
        gate("AV2_no_explicit_Corey_relperm_predictor_channels", len(overlap) == 0, overlap)

        # A0 scope: identify impact without choosing field statistics/subset.
        impact_rows = [
            {
                "quantity_or_module": "effective_saturation_Se",
                "directly_affected_by": "swc;sor",
                "AV3_A0_classification": "authority gap",
                "reason": "Se normalization currently uses scalar swc/sor.",
            },
            {
                "quantity_or_module": "krw_kro",
                "directly_affected_by": "nw;no;krw_max;kro_max;swc;sor",
                "AV3_A0_classification": "authority gap",
                "reason": "Relative permeability curves are currently globally constant.",
            },
            {
                "quantity_or_module": "fractional_flow_fw",
                "directly_affected_by": "nw;no;krw_max;kro_max;swc;sor",
                "AV3_A0_classification": "must be rebuilt for spatial constitutive fields",
                "reason": "Godunov transport flux uses fw(S).",
            },
            {
                "quantity_or_module": "advective_transport_CFL_and_wave_speed",
                "directly_affected_by": "spatial fw and dfw/dS",
                "AV3_A0_classification": "must be re-certified",
                "reason": "Teacher stability and shock propagation depend on the local constitutive law.",
            },
            {
                "quantity_or_module": "capillary_shape_dshape",
                "directly_affected_by": "no;kro_max;swc;sor plus fw dependence",
                "AV3_A0_classification": "must be rebuilt/re-certified",
                "reason": "AV2 dshape uses kro, fw, and effective saturation.",
            },
            {
                "quantity_or_module": "teacher_Y_transport",
                "directly_affected_by": "all selected AV3 constitutive fields",
                "AV3_A0_classification": "old AV2 teachers not authoritative for AV3",
                "reason": "Both advection and capillary operators change.",
            },
            {
                "quantity_or_module": "physics_residual",
                "directly_affected_by": "all selected AV3 constitutive fields",
                "AV3_A0_classification": "old AV2 residual not sufficient",
                "reason": "Residual must evaluate the same spatial constitutive law as the AV3 teacher.",
            },
            {
                "quantity_or_module": "PI_RNN_inputs",
                "directly_affected_by": "selected AV3 constitutive fields",
                "AV3_A0_classification": "new conditioning authority required",
                "reason": "Existing 9 channels contain no explicit Corey/relperm parameters.",
            },
            {
                "quantity_or_module": "AV2_epoch198_checkpoint",
                "directly_affected_by": "missing AV3 conditioning",
                "AV3_A0_classification": "not automatically authoritative",
                "reason": "Checkpoint was trained only under the frozen scalar AV2 constitutive vector.",
            },
            {
                "quantity_or_module": "pressure_Q",
                "directly_affected_by": "none under isolated AV3 transport-only scope",
                "AV3_A0_classification": "preserve AV2 authority in AV3; mobility feedback deferred to AV4",
                "reason": "AV3 isolates constitutive transport heterogeneity; dynamic pressure/total-mobility feedback is an AV4 problem.",
            },
            {
                "quantity_or_module": "Pollock_streamlines_and_TOF",
                "directly_affected_by": "none if pressure/Q and phi/K remain frozen",
                "AV3_A0_classification": "reuse AV2 kinematics",
                "reason": "Relperm-only transport heterogeneity does not alter the frozen velocity field in AV3.",
            },
            {
                "quantity_or_module": "R7D_S0_H1_D1_graph_geometry",
                "directly_affected_by": "none if AV2 kinematics remain frozen",
                "AV3_A0_classification": "reuse realization-specific AV2 graph geometry",
                "reason": "Graph membership follows exact Pollock paths; occupancy mass distribution may change.",
            },
            {
                "quantity_or_module": "local_pore_volume_capacity",
                "directly_affected_by": "swc;sor only if selected to vary",
                "AV3_A0_classification": "conditional authority gap",
                "reason": "Varying swc/sor changes admissible saturation endpoints and the 0.60 incremental-capacity semantics.",
            },
        ]

        gap = {
            "milestone": MILESTONE,
            "protocol_id": PROTOCOL_ID,
            "frozen_AV2_constitutive_vector": AV2_CONST,
            "current_AV2_predictor_channels": CURRENT_CHANNELS,
            "candidate_AV3_spatial_parameters_not_yet_selected": CANDIDATE_SPATIAL_PARAMETERS,
            "central_authority_gap": (
                "AV2 teacher, residual, and epoch-198 PI-RNN were built under one global "
                "Corey/relative-permeability constitutive vector. Independent spatial "
                "heterogeneity in these parameters is not represented in the existing "
                "9-channel predictor and therefore requires a prospectively frozen AV3 "
                "field/subset contract, new transport authorities, and new learning evidence."
            ),
            "swc_sor_special_case": (
                "If swc and/or sor are selected as spatial AV3 fields, the change is broader "
                "than varying only Corey exponents/endpoints: effective-saturation normalization, "
                "inlet/initial saturation definitions, admissible saturation bounds, and grid "
                "incremental-capacity semantics must be explicitly redesigned and re-certified."
            ),
            "pressure_scope": (
                "AV3 is prospectively isolated as a transport-constitutive heterogeneity stage. "
                "Pressure/Q and exact Pollock/TOF kinematics remain inherited from AV2. "
                "Relperm-driven total-mobility pressure refresh is deferred to AV4."
            ),
        }

        scope = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "AV3_parameter_subset_selected_in_A0": False,
            "AV3_parameter_distributions_selected_in_A0": False,
            "AV3_parameter_correlations_selected_in_A0": False,
            "AV3_spatial_fields_generated_in_A0": False,
            "teacher_generated_in_A0": False,
            "training_in_A0": False,
            "inference_in_A0": False,
            "pressure_resolve_in_A0": False,
            "Pollock_retrace_in_A0": False,
            "mapback_in_A0": False,
            "LP_execution_in_A0": False,
            "CMG_in_A0": False,
            "preserve_from_AV2": [
                "SGSim permeability realization",
                "four frozen AV2 porosity realizations and split identities",
                "five-spot wells and controls",
                "AV2 pressure/Q fields",
                "AV2 realization-specific Pollock streamlines and TOF",
                "AV2 local-pore-volume grid capacity unless swc/sor are later selected to vary",
                "R7D terminal-halo construction rule and AV2 realization-specific graph geometry",
                "immutable AV2 checkpoint and OOD evidence as historical baseline only",
            ],
            "must_not_assume": [
                "AV2 epoch-198 checkpoint is predictive authority for AV3",
                "AV2 teacher targets are valid under spatial Corey/relperm heterogeneity",
                "AV2 physics residual remains valid without constitutive-field conditioning",
                "swc/sor can vary without changing saturation/capacity semantics",
                "AV3 establishes pressure-mobility feedback; that is deferred to AV4",
            ],
        }

        next_contract = {
            "milestone": "POSTV16-AV3-A1",
            "name": "Spatial Corey / Relative-Permeability Parameter-Subset, Field-Model, Correlation, Bounds, and Split-Registry Freeze",
            "authorized": True,
            "execution": False,
            "required_decisions": [
                "which subset of nw,no,krw_max,kro_max,swc,sor is spatially variable",
                "hard physical bounds for each selected parameter",
                "spatial correlation structure and relationship to K and phi",
                "whether selected fields are independent or cross-correlated",
                "train/validation/locked-OOD realization registry",
                "whether swc/sor remain fixed; if not, define new saturation-bound and grid-capacity semantics",
                "new predictor conditioning channels required by selected constitutive fields",
            ],
        }

        decision = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "protocol_id": PROTOCOL_ID,
            "AV2_final_outcome_bound": True,
            "AV2_checkpoint_sha256": CKSHA,
            "AV3_authority_gap_identified": True,
            "AV2_checkpoint_authoritative_for_AV3": False,
            "AV2_teacher_authoritative_for_AV3": False,
            "AV2_physics_residual_authoritative_for_AV3_without_modification": False,
            "pressure_Q_reuse_authorized_within_AV3_transport_only_scope": True,
            "AV2_Pollock_TOF_reuse_authorized_within_AV3_transport_only_scope": True,
            "AV2_R7D_graph_geometry_reuse_authorized_within_AV3_transport_only_scope": True,
            "swc_sor_variation_requires_explicit_A1_semantics": True,
            "parameter_subset_frozen": False,
            "field_generation_performed": False,
            "teacher_generation_performed": False,
            "training_performed": False,
            "inference_performed": False,
            "pressure_resolve_performed": False,
            "Pollock_retrace_performed": False,
            "mapback_performed": False,
            "LP_execution_performed": False,
            "CMG_validation_performed": False,
            "AV3_A1_authorized": True,
            "next": next_contract,
        }

        summary = {
            "milestone": MILESTONE,
            "status": STATUS_PASS,
            "protocol_id": PROTOCOL_ID,
            "AV2_checkpoint_sha256": CKSHA,
            "candidate_spatial_parameter_count": len(CANDIDATE_SPATIAL_PARAMETERS),
            "current_AV2_input_channels": len(CURRENT_CHANNELS),
            "parameter_subset_selected": False,
            "field_generation": False,
            "teacher_generation": False,
            "training": False,
            "inference": False,
            "pressure_resolve": False,
            "Pollock_retrace": False,
            "mapback": False,
            "LP_execution": False,
            "CMG_validation": False,
            "AV3_A1_authorized": True,
            "next": next_contract,
        }

        files = {
            "PAD_Stream_POSTV16_AV3_A0_Summary.json": json_bytes(summary),
            "POSTV16_AV3_A0_Current_AV2_Constitutive_Authority.json": json_bytes({
                "frozen_constitutive_vector": AV2_CONST,
                "current_predictor_channels": CURRENT_CHANNELS,
                "checkpoint_sha256": CKSHA,
            }),
            "POSTV16_AV3_A0_Authority_Gap.json": json_bytes(gap),
            "POSTV16_AV3_A0_Physics_Impact_Matrix.csv": csv_bytes(impact_rows),
            "POSTV16_AV3_A0_Prospective_Scope_Contract.json": json_bytes(scope),
            "POSTV16_AV3_A0_A1_Handoff_Contract.json": json_bytes(next_contract),
            "POSTV16_AV3_A0_Decision_Contract.json": json_bytes(decision),
            "POSTV16_AV3_A0_Final_Gate_Matrix.csv": csv_bytes(
                [{"gate": k, **v} for k, v in gates.items()]
            ),
        }

        immutable_publish(out, files)

        manifest_rows = []
        for q in sorted(out.iterdir()):
            if q.is_file() and q.name != "POSTV16_AV3_A0_Artifact_Manifest.csv":
                manifest_rows.append({
                    "file": q.name,
                    "sha256": sha256_file(q),
                    "bytes": q.stat().st_size,
                })

        immutable_publish(
            out,
            {"POSTV16_AV3_A0_Artifact_Manifest.csv": csv_bytes(manifest_rows)},
        )

        print()
        print("=" * 198)
        print("POSTV16-AV3-A0: FULL AUTHORITY-GAP / PHYSICS-IMPACT FREEZE PASS")
        print("=" * 198)
        print("AV2 final outcome bound                         : True")
        print("Frozen AV2 checkpoint                          :", CKSHA)
        print("Current AV2 input channels                     : 9")
        print("Candidate AV3 spatial constitutive parameters  : 6")
        print("AV2 checkpoint authoritative for AV3           : False")
        print("AV2 teacher authoritative for AV3              : False")
        print("Pressure/Q reused in AV3 transport-only scope  : True")
        print("Pollock/TOF reused in AV3 transport-only scope : True")
        print("R7D graph geometry reused in AV3               : True")
        print("swc/sor special semantics required if varied   : True")
        print("Parameter subset chosen in A0                  : False")
        print("Field generation / teacher / training          : False / False / False")
        print("POSTV16-AV3-A1                                 : AUTHORIZED")
        print("AV3 execution                                  : NOT YET AUTHORIZED")
        print("=" * 198)
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
            "AV3_A1_authorized": False,
        }
        q = blocked / "POSTV16_AV3_A0_Blocked_Report.json"
        if not q.exists():
            q.write_bytes(json_bytes(report))

        print()
        print("POSTV16-AV3-A0: BLOCKED", stage, repr(exc))
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
