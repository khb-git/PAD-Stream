from pathlib import Path
import hashlib
import json
import os


# =============================================================================
# PAD-Stream V16E-1B2CUDA8G
#
# Stage-2 Architecture Redesign and New Certification Protocol Freeze
#
# PURPOSE
# -------
# Freeze the scientific redesign after the valid negative CUDA8E Stage-2
# certification result and the read-only CUDA8F failed-gate forensic.
#
# THIS MILESTONE:
#   - freezes COMP007 as an immutable non-certified Stage-2 artifact;
#   - retires the opened original holdout from future certification;
#   - freezes a bounded-monotone cumulative-decrement saturation architecture;
#   - freezes a NEW source-native DEV dataset protocol;
#   - freezes a NEW blind source-native CERTIFICATION dataset protocol;
#   - allows injector-side Nc=0 derivative investigation on DEV only;
#   - preserves the original Stage-2 certification principles.
#
# THIS MILESTONE DOES NOT:
#   - generate datasets;
#   - train COMP008;
#   - inspect the new blind certification set;
#   - change the original CUDA8E disposition;
#   - authorize B3;
#   - use OOD or TOF data.
# =============================================================================


MILESTONE = "V16E-1B2CUDA8G"
PROSPECTIVE_EXPERIMENT = "V16E-BLREP-COMP-CUDA-008"


REPO = Path("/content/PAD-Stream")
DRIVE = Path("/content/drive/MyDrive/PAD_Stream_Compute")


CUDA8E_SOURCE = (
    REPO
    / "PAD_Stream_V16E1B2CUDA8E_COMP007_PostTraining_Stage2_Closure_Evaluation.py"
)

CUDA8F_SOURCE = (
    REPO
    / "PAD_Stream_V16E1B2CUDA8F_Stage2_Failed_Gate_Evidence_Review.py"
)

CUDA8E_ROOT = (
    DRIVE
    / "provenance"
    / "stage2_repair"
    / "V16E1B2CUDA8E_COMP007_STAGE2_POSTTRAINING_CLOSURE"
)

CUDA8E_RESULTS = (
    CUDA8E_ROOT
    / "V16E1B2CUDA8E_COMP007_Stage2_Closure_Results.json"
)

CUDA8E_DISPOSITION = (
    CUDA8E_ROOT
    / "V16E1B2CUDA8E_COMP007_Stage2_Disposition.json"
)

CUDA8F_ROOT = (
    DRIVE
    / "provenance"
    / "stage2_repair"
    / "V16E1B2CUDA8F_STAGE2_FAILED_GATE_EVIDENCE_REVIEW"
)

CUDA8F_RESULTS = (
    CUDA8F_ROOT
    / "V16E1B2CUDA8F_Failed_Gate_Evidence_Review.json"
)

CUDA8F_SUMMARY = (
    CUDA8F_ROOT
    / "PAD_Stream_V16E1B2CUDA8F_Summary.json"
)

CUDA8F_HANDOFF = (
    CUDA8F_ROOT
    / "V16E1B2CUDA8F_Handoff.md"
)


PROVENANCE_ROOT = (
    DRIVE
    / "provenance"
    / "stage2_redesign"
    / "V16E1B2CUDA8G_ARCHITECTURE_AND_CERTIFICATION_PROTOCOL_FREEZE"
)

PROVENANCE_ROOT.mkdir(
    parents=True,
    exist_ok=True,
)

ARCHITECTURE_PATH = (
    PROVENANCE_ROOT
    / "V16E1B2CUDA8G_COMP008_Bounded_Monotone_Architecture_Protocol.json"
)

DATA_PROTOCOL_PATH = (
    PROVENANCE_ROOT
    / "V16E1B2CUDA8G_New_SourceNative_Data_Protocol.json"
)

CERTIFICATION_PATH = (
    PROVENANCE_ROOT
    / "V16E1B2CUDA8G_Stage2_Certification_Protocol.json"
)

SUMMARY_PATH = (
    PROVENANCE_ROOT
    / "PAD_Stream_V16E1B2CUDA8G_Summary.json"
)

HANDOFF_PATH = (
    PROVENANCE_ROOT
    / "V16E1B2CUDA8G_Handoff.md"
)


EXPECTED = {
    "CUDA8E_SOURCE":
        "41c9bc07388130274f9cd06b043eafa3669f21ef81746f4bb8f7f23b57736eba",

    "CUDA8F_SOURCE":
        "e0d5543fadcb73d5791a8acf8b0913e3ebfd5237a23b7c701b2282878811ed49",

    "CUDA8E_RESULTS":
        "cf8c38345083dc50484c74de5289f84320bf1f75b6ee75e459fec67d08e0da5a",

    "CUDA8E_DISPOSITION":
        "9b9a3627d9de9ea9fb36e4233e910ddc5c686ab062b3f6aa2673a8ede4d10026",

    "CUDA8F_RESULTS":
        "d3f783a96a7bae02e3a387e6e156f8718acff45a0fee804f0a676e1af588332a",

    "CUDA8F_SUMMARY":
        "550bc482b70c5e0162dacced2db8a5b2a03568e8e86dbf8277681397a11b8c5d",

    "CUDA8F_HANDOFF":
        "f8291e53a1d6a350ea1c38e82c5e6c3adee2103db2d3d7c3949270ac4e38ebac",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        for block in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(block)

    return h.hexdigest()


def gate(name, condition):
    ok = bool(condition)

    print(
        f"[{'PASS' if ok else 'FAIL'}] {name}"
    )

    if not ok:
        raise RuntimeError(
            f"CUDA8G freeze gate failed: {name}"
        )


def atomic_json(path: Path, obj):
    tmp = Path(
        str(path)
        + ".tmp"
    )

    with tmp.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            obj,
            f,
            indent=2,
            allow_nan=False,
        )

        f.write("\n")
        f.flush()
        os.fsync(
            f.fileno()
        )

    os.replace(
        tmp,
        path,
    )


print("=" * 110)
print("PAD-Stream V16E-1B2CUDA8G")
print("Stage-2 Architecture Redesign and New Certification Protocol Freeze")
print("=" * 110)

print()
print("NO TRAINING.")
print("NO DATASET GENERATION.")
print("NO NEW CERTIFICATION-SET INSPECTION.")
print("NO OOD.")
print("NO TOF.")
print("B3 REMAINS BLOCKED.")
print()


AUTHORITY = {
    "CUDA8E_SOURCE":
        CUDA8E_SOURCE,

    "CUDA8F_SOURCE":
        CUDA8F_SOURCE,

    "CUDA8E_RESULTS":
        CUDA8E_RESULTS,

    "CUDA8E_DISPOSITION":
        CUDA8E_DISPOSITION,

    "CUDA8F_RESULTS":
        CUDA8F_RESULTS,

    "CUDA8F_SUMMARY":
        CUDA8F_SUMMARY,

    "CUDA8F_HANDOFF":
        CUDA8F_HANDOFF,
}


print("FROZEN EVIDENCE AUTHORITY GATES")

for name, path in AUTHORITY.items():
    gate(
        f"{name}_exists",
        path.exists(),
    )

    gate(
        f"{name}_SHA_exact",
        sha256(path)
        ==
        EXPECTED[name],
    )


cuda8e = json.loads(
    CUDA8E_RESULTS.read_text(
        encoding="utf-8"
    )
)

cuda8f = json.loads(
    CUDA8F_RESULTS.read_text(
        encoding="utf-8"
    )
)


print()
print("SCIENTIFIC DISPOSITION GATES")

gate(
    "CUDA8E_Stage2_not_certified",
    cuda8e[
        "Stage2_certified"
    ]
    is False,
)

gate(
    "CUDA8E_B3_not_authorized",
    cuda8e[
        "B3_authorized"
    ]
    is False,
)

gate(
    "CUDA8F_retraining_not_authorized",
    cuda8f[
        "retraining_authorized"
    ]
    is False,
)

gate(
    "CUDA8F_B3_not_authorized",
    cuda8f[
        "B3_authorized"
    ]
    is False,
)


# =============================================================================
# Freeze architecture redesign
# =============================================================================

ARCHITECTURE = {
    "milestone":
        MILESTONE,

    "prospective_experiment":
        PROSPECTIVE_EXPERIMENT,

    "status":
        "ARCHITECTURE_PROTOCOL_FROZEN_IMPLEMENTATION_NOT_YET_AUTHORIZED",

    "scientific_motivation": {
        "CUDA8E_failed_gates": [
            "Nc0_corrected_residual_RMSE",
            "monotonicity_violation_fraction",
            "upper_saturation_bound",
        ],

        "CUDA8F_localization": {
            "Nc0_corrected_residual":
                "dominant excess localized near injector-side xi approximately 0.016 to 0.159",

            "monotonicity":
                "dominant violations localized near shock-tip side xi approximately 0.84 to 1.00",

            "upper_bound":
                "small-amplitude but distributed interior overshoot",
        },

        "design_principle":
            (
                "Move endpoint, monotonicity, and saturation-bound physics "
                "from soft penalties into the output parameterization itself."
            ),
    },

    "recurrent_trunk": {
        "coordinate_inputs":
            [
                "xi",
                "eta",
            ],

        "physical_parameter_input":
            "p11 unchanged from COMP007",

        "hidden_size":
            64,

        "recurrent_layers":
            2,

        "recurrent_family":
            "LSTM",

        "change_relative_to_COMP007":
            "output parameterization only; recurrent trunk retained for controlled comparison",
    },

    "bounded_monotone_parameterization": {
        "raw_output":
            (
                "network predicts nodewise latent logits z_i on the native xi sequence"
            ),

        "interval_positive_decrements":
            (
                "q_j = softplus(0.5*(z_j + z_{j+1})) + epsilon, "
                "for j=0,...,N-2"
            ),

        "epsilon":
            1.0e-8,

        "normalized_interval_weights":
            "w_j = q_j / sum_k(q_k)",

        "cumulative_coordinate":
            (
                "C_0=0; C_i=sum_{j=0}^{i-1} w_j for interior nodes; C_{N-1}=1 exactly"
            ),

        "saturation_construction":
            (
                "S_i = S_inj - (S_inj - Sw_star) * C_i"
            ),

        "S_inj":
            "1 - Sor",

        "Sw_star":
            "p11 index 9 frozen Rankine-Hugoniot shock-state authority",

        "architectural_guarantees": [
            "S(xi=0) = S_inj exactly",
            "S(xi=1) = Sw_star exactly",
            "Sw_star <= S(xi) <= S_inj for every node",
            "S_{i+1} <= S_i for every adjacent pair",
            "monotonicity penalty is not required for physical enforcement",
        ],

        "required_preflight_checks": [
            "exact endpoints to numerical tolerance",
            "zero upper-bound violation to numerical tolerance",
            "zero lower-bound violation to numerical tolerance",
            "zero positive-slope monotonicity violations to numerical tolerance",
            "finite first derivatives",
            "finite corrected conservative residual",
            "finite backward graph",
        ],
    },

    "loss_policy": {
        "data_loss":
            "retain source-native saturation data loss",

        "corrected_physics_loss":
            "retain corrected conservative Stage-2 PDE residual",

        "anchor_loss":
            "retain only if independently justified on development data",

        "injector_BC_loss":
            "remove as optimization objective once exact architectural endpoint is verified",

        "tip_BC_loss":
            "remove as optimization objective once exact architectural endpoint is verified",

        "monotonicity_loss":
            "remove as optimization objective; monotonicity is architectural",

        "bounds_penalty":
            "do not add; bounds are architectural",
    },

    "Nc0_injector_derivative_issue": {
        "status":
            "DEVELOPMENT_DIAGNOSTIC_REQUIRED_BEFORE_SPECIAL_TREATMENT",

        "known_retrospective_evidence":
            (
                "CUDA8F localized the COMP007 Nc=0 corrected-residual excess "
                "primarily to xi approximately 0.016-0.159."
            ),

        "allowed_next_action":
            (
                "test whether the same injector-side corrected-residual pattern "
                "appears on the NEW DEV dataset"
            ),

        "forbidden_action":
            (
                "design or tune an inlet-specific repair against the retired original holdout"
            ),

        "special_inlet_term_authorized_now":
            False,
    },

    "COMP007_status": {
        "immutable":
            True,

        "Stage2_certified":
            False,

        "role":
            (
                "frozen first-generation corrected-physics compressible PI-RNN "
                "and retrospective redesign evidence"
            ),
    },
}


# =============================================================================
# Freeze new source-native data protocol
# =============================================================================

DATA_PROTOCOL = {
    "milestone":
        MILESTONE,

    "status":
        "NEW_DATA_PROTOCOL_FROZEN_DATASETS_NOT_YET_GENERATED",

    "distribution": {
        "relationship_to_original_Stage2_generator":
            "IID/source-native; same frozen parameter distributions and physics generator",

        "OOD":
            False,

        "coordinate_nodes_per_profile":
            64,

        "times_per_case":
            6,

        "teacher":
            "same frozen Stage-2 Godunov/source-native teacher authority",

        "parameterization":
            "same p11 semantics and same Nc strata as prior Stage-2 work",

        "Nc_values": [
            0.00,
            0.05,
            0.10,
            0.20,
            0.30,
        ],
    },

    "original_data_roles_after_CUDA8G": {
        "original_train_11520":
            "retained as primary model-training set",

        "original_holdout_2880":
            (
                "RETIRED FROM FUTURE CERTIFICATION; may be cited only as "
                "retrospective CUDA8E/CUDA8F evidence"
            ),

        "original_holdout_may_be_used_for_training":
            False,

        "original_holdout_may_be_used_for_model_selection":
            False,

        "original_holdout_may_be_used_for_threshold_tuning":
            False,
    },

    "new_development_set": {
        "seed":
            20260918,

        "cases":
            480,

        "times_per_case":
            6,

        "profiles":
            2880,

        "role":
            (
                "development diagnostics, architecture selection, optimizer/loss "
                "selection, and Nc=0 inlet-derivative investigation"
            ),

        "may_be_inspected_during_development":
            True,

        "may_be_used_for_final_blind_certification":
            False,
    },

    "new_blind_certification_set": {
        "seed":
            20260919,

        "cases":
            480,

        "times_per_case":
            6,

        "profiles":
            2880,

        "role":
            "single-use final Stage-2 certification",

        "may_be_inspected_during_development":
            False,

        "may_be_used_for_model_selection":
            False,

        "may_be_used_for_threshold_tuning":
            False,

        "must_be_generated_and_hashed_before_COMP008_training":
            True,

        "must_remain_sealed_until_final_COMP008_checkpoint_is_frozen":
            True,
    },

    "dataset_generation_order": [
        "generate DEV dataset and freeze SHA",
        "generate blind CERT dataset and freeze SHA without scientific inspection",
        "freeze split/role manifests",
        "only then begin COMP008 implementation/training",
    ],
}


# =============================================================================
# Freeze future Stage-2 certification principles
# =============================================================================

CERTIFICATION = {
    "milestone":
        MILESTONE,

    "status":
        "CERTIFICATION_PRINCIPLES_FROZEN_BLIND_SET_NOT_YET_GENERATED",

    "blind_test_policy": {
        "set":
            "new seed-20260919 source-native certification set",

        "single_use":
            True,

        "open_only_after":
            (
                "COMP008 architecture, optimizer, training horizon, and final checkpoint "
                "are frozen without access to certification results"
            ),

        "if_failed":
            (
                "failure is recorded; no repeated tuning against the same blind certification set"
            ),
    },

    "comparison_models_on_new_blind_set": [
        "COMP004",
        "COMP005",
        "COMP007",
        "COMP008",
    ],

    "acceptance_principles": {
        "preserve_COMP005": [
            "global source-native RMSE",
            "Nc>0 source-native RMSE",
            "global corrected-residual RMSE",
            "Nc>0 corrected-residual RMSE",
        ],

        "restore_or_beat_COMP004": [
            "Nc=0 source-native RMSE",
            "Nc=0 corrected-residual RMSE",
            "tip/shock-state error",
            "monotonicity violation fraction",
        ],

        "absolute_physical_gates": [
            "finite predictions",
            "finite corrected residual",
            "lower saturation bound",
            "upper saturation bound",
            "injector endpoint",
            "Rankine-Hugoniot tip endpoint",
        ],

        "all_required":
            True,

        "partial_pass_does_not_certify":
            True,
    },

    "physical_tolerances": {
        "bound_tolerance":
            1.0e-6,

        "endpoint_tolerance":
            1.0e-6,
    },

    "architecture_expectation_not_acceptance_relaxation": {
        "monotonicity":
            "COMP008 architecture is expected to make violation fraction numerically zero",

        "bounds":
            "COMP008 architecture is expected to satisfy upper/lower bounds numerically exactly",

        "note":
            (
                "These architectural expectations do not weaken or replace the frozen "
                "certification gates."
            ),
    },

    "B3_policy": {
        "authorized_only_if_all_Stage2_gates_pass":
            True,

        "current_B3_authorized":
            False,
    },
}


atomic_json(
    ARCHITECTURE_PATH,
    ARCHITECTURE,
)

ARCHITECTURE_SHA = sha256(
    ARCHITECTURE_PATH
)


atomic_json(
    DATA_PROTOCOL_PATH,
    DATA_PROTOCOL,
)

DATA_PROTOCOL_SHA = sha256(
    DATA_PROTOCOL_PATH
)


atomic_json(
    CERTIFICATION_PATH,
    CERTIFICATION,
)

CERTIFICATION_SHA = sha256(
    CERTIFICATION_PATH
)


RUNNER_SHA = sha256(
    Path(
        __file__
    )
)


SUMMARY = {
    "milestone":
        MILESTONE,

    "runner_sha256":
        RUNNER_SHA,

    "architecture_protocol_sha256":
        ARCHITECTURE_SHA,

    "data_protocol_sha256":
        DATA_PROTOCOL_SHA,

    "certification_protocol_sha256":
        CERTIFICATION_SHA,

    "COMP007_immutable":
        True,

    "COMP007_Stage2_certified":
        False,

    "original_holdout_retired_from_future_certification":
        True,

    "new_DEV_seed":
        20260918,

    "new_blind_CERT_seed":
        20260919,

    "prospective_experiment":
        PROSPECTIVE_EXPERIMENT,

    "COMP008_implementation_authorized":
        False,

    "dataset_generation_authorized":
        True,

    "B3_authorized":
        False,

    "next_milestone":
        (
            "V16E-1B2CUDA8H — Generate and freeze the new IID/source-native "
            "DEV and blind CERT datasets; no model training"
        ),
}


atomic_json(
    SUMMARY_PATH,
    SUMMARY,
)

SUMMARY_SHA = sha256(
    SUMMARY_PATH
)


HANDOFF = f"""# PAD-Stream V16E-1B2CUDA8G

## Status

Stage-2 architecture redesign and new certification protocol are frozen.

No training occurred.

COMP007 remains immutable and non-certified.

The original 2,880-profile holdout is retired from future certification and
retained only as retrospective CUDA8E/CUDA8F evidence.

## COMP008 architecture

The recurrent trunk remains the controlled COMP007-style LSTM trunk.

The output representation changes to a bounded monotone cumulative-decrement
construction:

1. predict latent node logits z_i;
2. construct positive interval decrements with softplus;
3. normalize interval decrements;
4. cumulatively integrate from 0 to 1;
5. map the cumulative coordinate between S_inj and Sw_star.

This makes the following exact by construction:

- injector endpoint;
- shock-tip endpoint;
- lower/upper saturation bounds;
- non-increasing saturation along xi.

Monotonicity is therefore removed as a soft optimization objective.

## Nc=0 injector-side residual

CUDA8F's xi≈0.016-0.159 localization is treated as retrospective evidence.

No inlet-specific repair is authorized yet.

The same phenomenon must first be tested independently on the new DEV dataset.

## New data firewall

DEV:
- seed 20260918
- 480 cases
- 6 times per case
- 2,880 profiles
- inspectable during development

Blind certification:
- seed 20260919
- 480 cases
- 6 times per case
- 2,880 profiles
- generated and hashed before COMP008 training
- sealed until the final COMP008 checkpoint is frozen

Both datasets remain IID/source-native, not OOD.

## Stage-2 certification

The same scientific principles are retained:

- preserve COMP005 global and positive-Nc accuracy/physics;
- restore or beat COMP004 Nc=0, tip, and monotonicity behavior;
- satisfy absolute physical gates;
- all gates required.

B3 remains blocked until a new blind Stage-2 certification passes.

## Hashes

CUDA8G runner SHA-256:

`{RUNNER_SHA}`

Architecture protocol SHA-256:

`{ARCHITECTURE_SHA}`

Data protocol SHA-256:

`{DATA_PROTOCOL_SHA}`

Certification protocol SHA-256:

`{CERTIFICATION_SHA}`

Summary SHA-256:

`{SUMMARY_SHA}`

## Next

`V16E-1B2CUDA8H — Generate and freeze new source-native DEV and blind CERT datasets; no model training`
"""


HANDOFF_PATH.write_text(
    HANDOFF,
    encoding="utf-8",
)

HANDOFF_SHA = sha256(
    HANDOFF_PATH
)


print()
print("=" * 110)
print("CUDA8G RESULT")
print("=" * 110)

print(
    "Architecture protocol SHA :",
    ARCHITECTURE_SHA,
)

print(
    "Data protocol SHA         :",
    DATA_PROTOCOL_SHA,
)

print(
    "Certification protocol SHA:",
    CERTIFICATION_SHA,
)

print(
    "Summary SHA               :",
    SUMMARY_SHA,
)

print(
    "Handoff SHA               :",
    HANDOFF_SHA,
)

print(
    "Runner SHA                :",
    RUNNER_SHA,
)

print()
print("COMP007 IMMUTABLE: YES")
print("COMP007 STAGE 2 CERTIFIED: NO")
print("ORIGINAL HOLDOUT RETIRED FROM FUTURE CERTIFICATION: YES")
print("COMP008 IMPLEMENTATION AUTHORIZED: NO")
print("NEW DATASET GENERATION AUTHORIZED: YES")
print("B3 AUTHORIZED: NO")

print()
print(
    "NEXT: V16E-1B2CUDA8H — Generate and freeze new source-native DEV "
    "and blind CERT datasets; no model training"
)
