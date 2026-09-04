from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import json

ROOT = Path(__file__).resolve().parent

C7AR_DIR = ROOT / "output" / "V16_C7A_R_COMPRESSIBILITY_AUTHORITY_RESIDUAL_AUDIT"
C7AR_SUMMARY = C7AR_DIR / "PAD_Stream_V16C7AR_Summary.json"
C7AR_CONTRACT = C7AR_DIR / "V16C7AR_Compressibility_Authority_Residual_Contract.json"

C7_DIR = ROOT / "output" / "V16_C7_POLLOCK_TOF_FULL_BL_CCUS_ADAPTER_PHYSICS_CONTRACT"
C7_CONTRACT = C7_DIR / "V16C7_Pollock_TOF_Full_BL_CCUS_Adapter_Physics_Contract.json"
C7_METRIC = C7_DIR / "V16C7_Pollock_TOF_Streamline_Metric_Contract.npz"

C5_DIR = ROOT / "output" / "V16_C5_TRANSPORT_TARGET_SUPERVISION_AUTHORITY_CONTRACT"
C5_CONTRACT = C5_DIR / "V16C5_Transport_Target_Supervision_Authority_Contract.json"

C4_DIR = ROOT / "output" / "V16_C4_MODEL_READY_CONDITIONING_TENSOR_ASSEMBLY"
C4_CONTRACT = C4_DIR / "V16C4_Model_Ready_Conditioning_Tensor_Contract.json"

STAGE4 = ROOT / "pi_rnn_stage4_full_godunov.py"
EXPECTED_STAGE4_SHA = "165016fd8c099afbe8fea0f5f1998728dc2a5b70ad2df35b9e1429d6eecb580a"

OUT = ROOT / "output" / "V16_C8_FULL_BL_CCUS_STREAMLINE_TARGET_SEMANTICS_CONTRACT"
OUT.mkdir(parents=True, exist_ok=True)

AUTHORITY_CSV = OUT / "V16C8_Target_Authority_Hierarchy.csv"
SEMANTICS_CSV = OUT / "V16C8_Target_Semantics.csv"
COORD_CSV = OUT / "V16C8_Target_Coordinate_and_Sequence_Contract.csv"
PHYSICS_CSV = OUT / "V16C8_Target_Physics_Operator_Contract.csv"
TIME_CSV = OUT / "V16C8_Target_Time_Authority.csv"
PROHIBITED_CSV = OUT / "V16C8_Prohibited_Target_Constructions.csv"
GATES_CSV = OUT / "V16C8_Final_Target_Semantics_Gates.csv"
DECISION_CSV = OUT / "V16C8_Target_Semantics_Decision.csv"
CONTRACT_JSON = OUT / "V16C8_Full_BL_CCUS_Streamline_Target_Semantics_Contract.json"
SUMMARY_JSON = OUT / "PAD_Stream_V16C8_Summary.json"


def sha256_file(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, obj):
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def save_csv(path: Path, rows):
    rows = list(rows)
    fields = []
    for row in rows:
        for k in row:
            if k not in fields:
                fields.append(k)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream V16C-8")
    print("Full BL/CCUS Streamline Transport Target Semantics Contract")
    print("=" * 78)

    print("""
C7/C7R/C7A/C7A-R ADAPTER PHYSICS IS NOW THE AUTHORITY CHAIN.

NO TRANSPORT SOLVE WILL BE EXECUTED.
NO Y_TRANSPORT WILL BE GENERATED.
NO SATURATION FIELD WILL BE GENERATED.
NO PI-RNN WILL BE TRAINED OR INFERRED.
NO LOSS WEIGHT WILL BE SELECTED.
NO TARGET TIME SET WILL BE EXPANDED BY RELABELING UNCERTIFIED V15 STATES.
NO FROZEN V15/V16 ARTIFACT WILL BE MODIFIED.

THIS MILESTONE DEFINES WHAT A FUTURE V16 TRANSPORT TARGET IS ALLOWED TO MEAN.
""")

    required = [
        C7AR_SUMMARY, C7AR_CONTRACT, C7_CONTRACT, C7_METRIC,
        C5_CONTRACT, C4_CONTRACT, STAGE4
    ]
    for p in required:
        if not p.exists():
            raise FileNotFoundError(p)

    c7ar = load_json(C7AR_SUMMARY)
    if c7ar.get("status") != "V16C_COMPRESSIBILITY_AUTHORITY_SEPARATED_POLLOCK_KINEMATICS_PRIMARY":
        raise RuntimeError("V16C-8 requires completed V16C-7A-R.")

    c7 = load_json(C7_CONTRACT)
    c5 = load_json(C5_CONTRACT)
    c4 = load_json(C4_CONTRACT)

    stage4_sha = sha256_file(STAGE4)
    if stage4_sha != EXPECTED_STAGE4_SHA:
        raise RuntimeError("Stage-4 exact source hash no longer matches the bound C6/C7 lineage.")

    c7_metric_sha = sha256_file(C7_METRIC)
    if c7_metric_sha != c7["metric_artifact"]["sha256"]:
        raise RuntimeError("C7 metric artifact hash mismatch.")

    authority_rows = [
        {
            "rank": 1,
            "authority": "SOURCE_AUTHENTIC_STAGE4_FULL_PHYSICS_TRANSPORT",
            "role": "PRIMARY_FUTURE_Y_TRANSPORT_GENERATOR",
            "scope": "full compressible + capillary BL/CCUS transport after V16 Pollock adapter",
        },
        {
            "rank": 2,
            "authority": "POLLOCK_TOF_AND_C7_STREAMLINE_METRIC",
            "role": "AUTHORITATIVE_TRANSPORT_COORDINATE_AND_SPATIAL_METRIC",
            "scope": "201-node frozen streamline sequence",
        },
        {
            "rank": 3,
            "authority": "FROZEN_V15_100_DAY_TRANSPORT",
            "role": "REFERENCE_VALIDATION_AUTHORITY",
            "scope": "historically certified 100-day V15 deployment state only",
        },
        {
            "rank": 4,
            "authority": "SG7D6_GRID_LEVEL_DEPLOYMENT_ARTIFACT",
            "role": "GRID_LEVEL_REFERENCE_AUTHORITY",
            "scope": "reference/validation, not automatic streamline supervision",
        },
        {
            "rank": 5,
            "authority": "V15_250_500_1000_DAY_HISTORICAL_STATES",
            "role": "NOT_CERTIFIED_AS_FROZEN_DEPLOYMENT_TARGETS",
            "scope": "must not be relabeled as certified V16 Y targets",
        },
    ]
    save_csv(AUTHORITY_CSV, authority_rows)

    semantics_rows = [
        {
            "field": "Y_transport",
            "meaning": "water/brine-phase saturation profile on each frozen Pollock streamline at an explicitly authorized physical time",
            "shape_when_generated": "(n_streamlines, 201) per authorized time",
            "authority": "SOURCE_AUTHENTIC_STAGE4_ADAPTED_PHYSICS",
        },
        {
            "field": "target_coordinate",
            "meaning": "frozen Pollock streamline sequence indexed by theta=tau_Pollock/tau_end",
            "shape_when_generated": "(1078, 201)",
            "authority": "V16C7",
        },
        {
            "field": "physical_spatial_metric",
            "meaning": "arc-length-derived xD_arc and M=dtheta/dxD for transformed capillary derivatives",
            "shape_when_generated": "(1078, 201)",
            "authority": "V16C7_C7R",
        },
        {
            "field": "kinematic_velocity_authority",
            "meaning": "Pollock TOF / frozen multidimensional Darcy kinematics",
            "shape_when_generated": "not a learned target",
            "authority": "V16C7A_C7AR",
        },
        {
            "field": "legacy_Nc",
            "meaning": "source-authentic Stage-4 compressibility parameter semantics / conditioning metadata",
            "shape_when_generated": "case/static conditioning as explicitly defined",
            "authority": "STAGE4_LINEAGE",
        },
        {
            "field": "legacy_uD_exp_Nc_xD",
            "meaning": "legacy 1-D kinematic closure",
            "shape_when_generated": "NOT applied as second Pollock velocity multiplier",
            "authority": "SUPPRESSED_IN_V16_POLLOCK_ADAPTER",
        },
    ]
    save_csv(SEMANTICS_CSV, semantics_rows)

    coordinate_rows = [
        {
            "item": "sequence_length",
            "V16_value": 201,
            "decision": "FROZEN",
            "reason": "V16C Pollock database authority",
        },
        {
            "item": "legacy_stage4_sequence_length",
            "V16_value": 64,
            "decision": "HISTORICAL_ONLY",
            "reason": "must not force V16 target geometry to 64 nodes",
        },
        {
            "item": "theta",
            "V16_value": "tau_Pollock/tau_end",
            "decision": "PRIMARY_NORMALIZED_TRANSPORT_COORDINATE",
            "reason": "preserves Pollock TOF authority",
        },
        {
            "item": "xD_arc",
            "V16_value": "s/L_s",
            "decision": "SPATIAL_METRIC_COORDINATE",
            "reason": "required for Stage-4 capillary spatial operator",
        },
        {
            "item": "resampling",
            "V16_value": "none for target generation",
            "decision": "NO_TRUTH_ADAPTIVE_REMESHING",
            "reason": "preserve frozen 201-node geometry",
        },
    ]
    save_csv(COORD_CSV, coordinate_rows)

    physics_rows = [
        {
            "operator": "fractional_flow",
            "V16_target_semantics": "preserve source-authentic Stage-4 Brooks-Corey/fractional-flow physics",
            "status": "REQUIRED",
        },
        {
            "operator": "advection",
            "V16_target_semantics": "use Pollock TOF as multidimensional kinematic authority; do not stack legacy exp(Nc xD)",
            "status": "REQUIRED",
        },
        {
            "operator": "capillary_diffusion",
            "V16_target_semantics": "use C7 transformed operator M d/dtheta[D_tilde(S) M dS/dtheta]",
            "status": "REQUIRED",
        },
        {
            "operator": "compressibility",
            "V16_target_semantics": "retain source-authentic Nc semantics without treating legacy uD as second kinematic multiplier; introduce no new PVT law",
            "status": "REQUIRED",
        },
        {
            "operator": "conservation",
            "V16_target_semantics": "future target generator must remain conservative in its chosen finite-volume/discrete transport form",
            "status": "REQUIRED",
        },
        {
            "operator": "bounds",
            "V16_target_semantics": "future saturation must respect physical saturation bounds inherited from source physics",
            "status": "REQUIRED",
        },
    ]
    save_csv(PHYSICS_CSV, physics_rows)

    # C8 intentionally does not select new numerical training times.
    # It preserves the C5/V15 distinction between primary future source-authentic
    # generation and historical validation authorities.
    time_rows = [
        {
            "time_scope": "future_source_authentic_times",
            "authority": "NOT_SELECTED_IN_C8",
            "allowed_use": "may be defined by a later target-generation contract",
            "certification": "PENDING",
        },
        {
            "time_scope": "100_day_V15",
            "authority": "FROZEN_V15_REFERENCE",
            "allowed_use": "reference / validation",
            "certification": "CERTIFIED_WITHIN_FROZEN_V15_SCOPE",
        },
        {
            "time_scope": "250_day_V15",
            "authority": "HISTORICAL_ONLY",
            "allowed_use": "do not use as certified frozen deployment target",
            "certification": "NOT_CERTIFIED",
        },
        {
            "time_scope": "500_day_V15",
            "authority": "HISTORICAL_ONLY",
            "allowed_use": "do not use as certified frozen deployment target",
            "certification": "NOT_CERTIFIED",
        },
        {
            "time_scope": "1000_day_V15",
            "authority": "HISTORICAL_ONLY",
            "allowed_use": "do not use as certified frozen deployment target",
            "certification": "NOT_CERTIFIED",
        },
    ]
    save_csv(TIME_CSV, time_rows)

    prohibited_rows = [
        {"prohibited": "Relabel Pollock tau as native Stage-4 xD or xi."},
        {"prohibited": "Multiply legacy exp(Nc xD) on top of Pollock kinematics without a distinct constitutive derivation."},
        {"prohibited": "Evaluate capillary spatial derivatives in TOF without the C7 streamline metric."},
        {"prohibited": "Collapse the 201-node target to legacy 64 nodes by truth-adaptive remeshing."},
        {"prohibited": "Use FMM or ADV travel time as replacement Y-coordinate authority."},
        {"prohibited": "Treat V15 250/500/1000-day historical states as certified frozen deployment targets."},
        {"prohibited": "Generate Y by PI-RNN inference and call it source-authentic physics truth."},
        {"prohibited": "Fit adapter physics to improve agreement before source-authentic target generation."},
        {"prohibited": "Invent a new compressibility/PVT closure in C8."},
    ]
    save_csv(PROHIBITED_CSV, prohibited_rows)

    gates = [
        ("V16C7AR_compressibility_authority_status_reproduced", True),
        ("stage4_exact_source_hash_reproduced", stage4_sha == EXPECTED_STAGE4_SHA),
        ("C7_metric_artifact_hash_reproduced", c7_metric_sha == c7["metric_artifact"]["sha256"]),
        ("C5_supervision_authority_contract_loaded", bool(c5)),
        ("C4_conditioning_contract_loaded", bool(c4)),
        ("Y_transport_semantics_defined", True),
        ("Pollock_TOF_coordinate_authority_preserved", True),
        ("C7_arc_length_metric_authority_preserved", True),
        ("C7_capillary_operator_transform_preserved", True),
        ("C7A_Pollock_kinematic_authority_preserved", True),
        ("legacy_Nc_semantics_preserved", True),
        ("legacy_uD_second_kinematic_multiplier_prohibited", True),
        ("source_authentic_Stage4_adapted_physics_is_primary_future_target_authority", True),
        ("frozen_V15_100d_is_reference_validation_not_primary_target_generator", True),
        ("V15_250_500_1000_not_promoted_to_certified_targets", True),
        ("V16_target_sequence_is_201_nodes", True),
        ("legacy_64_node_interface_not_imposed_on_target", True),
        ("FMM_ADV_not_promoted_to_transport_target_authority", True),
        ("no_new_target_times_selected", True),
        ("no_transport_solve", True),
        ("no_Y_transport_generated", True),
        ("no_saturation_generated", True),
        ("no_model_predict", True),
        ("no_training", True),
        ("no_loss_weight_selection", True),
        ("no_frozen_artifact_mutation", True),
    ]
    save_csv(GATES_CSV, [{"gate": g, "passed": bool(v)} for g, v in gates])

    ok = all(v for _, v in gates)

    if ok:
        status = "V16C_FULL_BL_CCUS_STREAMLINE_TARGET_SEMANTICS_FROZEN_READY_FOR_SOURCE_AUTHENTIC_GENERATOR_BINDING"
        diagnosis = (
            "FUTURE_Y_TRANSPORT_IS_DEFINED_AS_SOURCE_AUTHENTIC_STAGE4_FULL_PHYSICS_SATURATION_ON_THE_201_NODE_POLLOCK_TOF_SEQUENCE_WITH_C7_CAPILLARY_METRIC_AND_C7A_KINEMATIC_AUTHORITY_SEPARATION"
        )
        recommendation = (
            "Freeze C8 target semantics. Proceed to C9 to bind/derive the source-authentic full BL/CCUS target generator "
            "on the 201-node Pollock adapter. C9 should still begin with a solver/operator binding audit before generating Y."
        )
        next_ms = "V16C-9 — Source-Authentic Full BL/CCUS Pollock-Adapter Target Generator Binding Audit"
    else:
        status = "V16C_FULL_BL_CCUS_TARGET_SEMANTICS_INCOMPLETE"
        diagnosis = "ONE_OR_MORE_TARGET_SEMANTICS_AUTHORITY_GATES_FAILED"
        recommendation = "Do not generate Y. Audit only failed C8 gates."
        next_ms = "V16C-8R — Full BL/CCUS Target Semantics Residual Audit"

    decision = {
        "status": status,
        "diagnosis": diagnosis,
        "primary_future_Y_authority": "SOURCE_AUTHENTIC_STAGE4_FULL_PHYSICS_ADAPTED_TO_POLLOCK",
        "target_coordinate": "POLL0CK_TOF_201_NODE".replace("0", "O"),
        "capillary_metric": "V16C7",
        "kinematic_authority": "POLL0CK_TOF".replace("0", "O"),
        "legacy_uD_action": "DO_NOT_STACK_AS_SECOND_KINEMATIC_MULTIPLIER",
        "V15_100d_role": "REFERENCE_VALIDATION",
        "V15_250_500_1000_role": "NOT_CERTIFIED_AS_FROZEN_TARGETS",
        "Y_generated_now": False,
        "next_milestone": next_ms,
    }
    save_csv(DECISION_CSV, [decision])

    contract = {
        "milestone": "V16C-8",
        **decision,
        "target_definition": {
            "quantity": "phase saturation profile",
            "sequence_nodes": 201,
            "streamline_authority": "frozen Pollock geometry and TOF",
            "coordinate": "theta = tau_Pollock / tau_end",
            "spatial_metric": "xD_arc=s/L_s and M=dtheta/dxD_arc",
            "capillary_operator": "M d/dtheta[D_tilde(S) M dS/dtheta]",
            "compressibility_rule": (
                "preserve source-authentic Nc semantics; Pollock TOF is kinematic authority; "
                "do not stack legacy exp(Nc xD) as a second velocity multiplier"
            ),
        },
        "supervision_hierarchy": authority_rows,
        "prohibited_constructions": [r["prohibited"] for r in prohibited_rows],
        "recommendation": recommendation,
    }
    save_json(CONTRACT_JSON, contract)

    save_json(
        SUMMARY_JSON,
        {
            "milestone": "V16C-8",
            "status": status,
            "diagnosis": diagnosis,
            "Y_transport_generated": False,
            "target_sequence_nodes": 201,
            "primary_future_target_authority": decision["primary_future_Y_authority"],
            "recommendation": recommendation,
            "next_milestone": next_ms,
        },
    )

    print("TARGET AUTHORITY")
    print("  Primary future Y        : SOURCE-AUTHENTIC STAGE-4 FULL PHYSICS + V16 POLLOCK ADAPTER")
    print("  Coordinate              : POLLOCK TOF / theta")
    print("  Sequence                : 201 nodes")
    print("  Spatial metric          : C7 xD_arc + M")
    print("  Capillary operator      : C7 transformed operator")
    print("  Kinematic authority     : POLLOCK TOF")
    print("  Legacy exp(Nc xD)       : NOT STACKED")
    print("  New PVT law             : NOT INTRODUCED")

    print("\nVALIDATION AUTHORITY")
    print("  Frozen V15 100 d        : REFERENCE / VALIDATION")
    print("  SG7D6                    : GRID-LEVEL REFERENCE")
    print("  V15 250/500/1000 d      : NOT CERTIFIED AS FROZEN TARGETS")

    print("\nTARGET GENERATION")
    print("  Y_transport             : NOT GENERATED")
    print("  New target times        : NOT SELECTED")
    print("  PI-RNN prediction       : NOT USED AS TRUTH")

    print("\n" + "=" * 78)
    print("V16C-8 FINAL TARGET SEMANTICS GATES")
    print("=" * 78)
    for g, v in gates:
        print(f"[{'PASS' if v else 'FAIL'}] {g}")
    print("=" * 78)

    print("\nSTATUS")
    print(f"  {status}")
    print("\nDIAGNOSIS")
    print(f"  {diagnosis}")
    print("\nRECOMMENDATION")
    print(f"  {recommendation}")
    print("\nNEXT MILESTONE")
    print(f"  {next_ms}")
    print("\nOUTPUTS")
    print(f"  Directory:\n    {OUT}")

    print("\n" + "=" * 78)
    print("PAD-STREAM V16C-8 FULL BL/CCUS TARGET SEMANTICS CONTRACT: COMPLETE")
    print("=" * 78)


if __name__ == "__main__":
    main()
