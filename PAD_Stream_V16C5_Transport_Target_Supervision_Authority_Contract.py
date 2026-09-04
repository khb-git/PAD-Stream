from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import json


# =============================================================================
# PAD-Stream V16C-5
# Transport Target / Supervision Authority Contract
#
# PURPOSE
# -------
# V16C-4 completed model-ready INPUT tensors but intentionally generated no
# transport target Y.
#
# V16C-5 freezes what is allowed to supervise a future PAD-Stream transport
# PI-RNN and, just as importantly, what is NOT allowed to be silently treated
# as training truth.
#
# CORE AUTHORITY DECISION
# -----------------------
#
# 1) Pollock TOF remains the authoritative streamline transport coordinate.
#
# 2) Future source-authentic BL/CCUS transport solved on the frozen Pollock
#    coordinate is the PRIMARY candidate for streamline transport supervision.
#
# 3) The frozen Version-15 100-day L2 deployment state is preserved as an
#    authoritative historical deployment/reference artifact, but it is NOT
#    automatically promoted to a V16C nodewise training target unless an exact
#    source-authentic mapping to the V16C streamline database is demonstrated.
#
# 4) SG7D6 remains a frozen grid-level deployment/reference artifact. It is not
#    a streamline-node target.
#
# 5) 250/500/1000-day frozen deployment states are NOT certified in frozen V15
#    and therefore may not be fabricated, relabelled, interpolated, or used as
#    supervision.
#
# 6) Physics losses may be used later, but their exact equations/weights must be
#    frozen in a later milestone before training.
#
# THIS MILESTONE DOES NOT GENERATE Y.
# =============================================================================


ROOT = Path(__file__).resolve().parent

C4_DIR = ROOT / "output" / "V16_C4_MODEL_READY_CONDITIONING_TENSOR_ASSEMBLY"
C4_TENSORS = C4_DIR / "V16C4_Model_Ready_Conditioning_Tensors.npz"
C4_SUMMARY = C4_DIR / "PAD_Stream_V16C4_Summary.json"
C4_CONTRACT = C4_DIR / "V16C4_Model_Ready_Conditioning_Tensor_Contract.json"

C3_DIR = ROOT / "output" / "V16_C3_PIRNN_TRANSPORT_CONDITIONING_CONTRACT"
C3_CONTRACT = C3_DIR / "V16C3_PIRNN_Transport_Conditioning_Contract.json"

C2_DIR = ROOT / "output" / "V16_C2_MULTI_COORDINATE_STREAMLINE_TRANSPORT_DATABASE"
C2_DB = C2_DIR / "V16C2_Multi_Coordinate_Streamline_Transport_Database.npz"

OUT = ROOT / "output" / "V16_C5_TRANSPORT_TARGET_SUPERVISION_AUTHORITY_CONTRACT"
OUT.mkdir(parents=True, exist_ok=True)

IDENTITY_CSV = OUT / "V16C5_Input_Identity.csv"
AUTHORITY_CSV = OUT / "V16C5_Transport_Supervision_Authority_Matrix.csv"
TARGET_CSV = OUT / "V16C5_Target_Class_Contract.csv"
PHYSICS_CSV = OUT / "V16C5_Physics_Supervision_Contract.csv"
V15_CSV = OUT / "V16C5_Frozen_V15_Reference_Scope.csv"
PROHIBIT_CSV = OUT / "V16C5_Prohibited_Target_Interpretations.csv"
HANDOFF_CSV = OUT / "V16C5_Transport_Target_Implementation_Handoff.csv"
GATES_CSV = OUT / "V16C5_Final_Supervision_Authority_Gates.csv"
DECISION_CSV = OUT / "V16C5_Supervision_Authority_Decision.csv"

CONTRACT_JSON = OUT / "V16C5_Transport_Target_Supervision_Authority_Contract.json"
SUMMARY_JSON = OUT / "PAD_Stream_V16C5_Summary.json"


def save_csv(path: Path, rows):
    rows = list(rows)
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    fields = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def save_json(path: Path, obj):
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def find_optional(patterns):
    hits = []
    for pattern in patterns:
        hits.extend(ROOT.glob(pattern))
    # unique + deterministic
    return sorted({p.resolve() for p in hits if p.is_file()})


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream V16C-5")
    print("Transport Target / Supervision Authority Contract")
    print("=" * 78)

    print("""
V16C-4 MODEL-READY INPUT TENSORS ARE IMMUTABLE.
POLLOCK TOF REMAINS THE AUTHORITATIVE STREAMLINE TRANSPORT COORDINATE.

NO Y_TRANSPORT TARGET WILL BE GENERATED.
NO TRANSPORT SOLVE WILL BE EXECUTED.
NO SATURATION FIELD WILL BE GENERATED.
NO PI-RNN WILL BE TRAINED.
NO MODEL.PREDICT CALL WILL BE EXECUTED.
NO GRID MAP-BACK WILL BE EXECUTED.
NO 250/500/1000-DAY STATE WILL BE GENERATED OR RELABELLED.
NO FROZEN V15 OR V16 ARTIFACT WILL BE CHANGED.

THIS MILESTONE DEFINES SUPERVISION AUTHORITY ONLY.
""")

    for p in [C4_TENSORS, C4_SUMMARY, C4_CONTRACT, C3_CONTRACT, C2_DB]:
        if not p.exists():
            raise FileNotFoundError(p)

    c4 = load_json(C4_SUMMARY)

    if c4.get("status") != "V16C_MODEL_READY_CONDITIONING_TENSORS_COMPLETE":
        raise RuntimeError("V16C-5 requires completed V16C-4.")

    # -------------------------------------------------------------------------
    # Supporting frozen-V15 provenance discovery.
    # This is supporting evidence only; the V15 scope decision has already been
    # frozen by the R19E/R20R/R21/R22/final-freeze branch.
    # -------------------------------------------------------------------------
    v15_scope_hits = find_optional([
        "output/V15_SG7E1R26IR19E/PAD_Stream_V15SG7E1R26IR19E_Summary.json",
        "output/V15_SG7E1R26IR20R/PAD_Stream_V15SG7E1R26IR20R_Summary.json",
        "output/V15_SG7E1R26IR21/PAD_Stream_V15SG7E1R26IR21_Summary.json",
        "output/V15_SG7E1R26IR22/PAD_Stream_V15SG7E1R26IR22_Summary.json",
        "output/V15_FINAL_FREEZE/**/*.json",
    ])

    save_csv(
        IDENTITY_CSV,
        [{
            "V16C2_database_sha256": sha256_file(C2_DB),
            "V16C3_contract_sha256": sha256_file(C3_CONTRACT),
            "V16C4_tensor_sha256": sha256_file(C4_TENSORS),
            "V16C4_contract_sha256": sha256_file(C4_CONTRACT),
            "supporting_V15_scope_records_found": len(v15_scope_hits),
        }],
    )

    authority_rows = [
        {
            "authority_class": "A0",
            "object": "Pollock TOF",
            "domain": "streamline-node",
            "role": "AUTHORITATIVE_TRANSPORT_COORDINATE",
            "eligible_as_future_Y": False,
            "eligible_as_future_input": True,
            "status": "FROZEN",
        },
        {
            "authority_class": "A1",
            "object": "Source-authentic BL/CCUS transport profile on frozen Pollock TOF",
            "domain": "streamline-node",
            "role": "PRIMARY_CANDIDATE_TRANSPORT_SUPERVISION",
            "eligible_as_future_Y": True,
            "eligible_as_future_input": False,
            "status": "NOT_YET_GENERATED_IN_V16C",
        },
        {
            "authority_class": "A2",
            "object": "Frozen V15 100-day L2 deployment state",
            "domain": "historical deployment state",
            "role": "AUTHORITATIVE_REFERENCE_VALIDATION_STATE",
            "eligible_as_future_Y": "ONLY_AFTER_EXACT_MAPPING_AUDIT",
            "eligible_as_future_input": False,
            "status": "PRESERVED",
        },
        {
            "authority_class": "A3",
            "object": "SG7D6 frozen grid deployment artifact",
            "domain": "grid",
            "role": "GRID_LEVEL_REFERENCE_VALIDATION",
            "eligible_as_future_Y": False,
            "eligible_as_future_input": False,
            "status": "PRESERVED",
        },
        {
            "authority_class": "A4",
            "object": "250/500/1000-day frozen V15 deployment states",
            "domain": "deployment",
            "role": "UNAVAILABLE",
            "eligible_as_future_Y": False,
            "eligible_as_future_input": False,
            "status": "NOT_CERTIFIED_NOT_RECOVERABLE",
        },
    ]
    save_csv(AUTHORITY_CSV, authority_rows)

    target_rows = [
        {
            "target_class": "T0",
            "name": "NO_TARGET",
            "definition": "V16C-5 itself",
            "authorized_now": True,
            "purpose": "preserve design/training separation",
        },
        {
            "target_class": "T1",
            "name": "STREAMLINE_SATURATION_PROFILE",
            "definition": "S_CO2 or equivalent transport state evaluated on frozen Pollock nodes",
            "authorized_now": False,
            "future_authority": "source-authentic BL/CCUS transport physics",
        },
        {
            "target_class": "T2",
            "name": "RESIDUAL_OR_CORRECTION_TARGET",
            "definition": "difference between physics baseline and learned correction",
            "authorized_now": False,
            "future_authority": "requires separately frozen hybrid PI-RNN contract",
        },
        {
            "target_class": "T3",
            "name": "GRID_SATURATION_TARGET",
            "definition": "full-grid mapped saturation",
            "authorized_now": False,
            "future_authority": "belongs after conservative map-back contract",
        },
    ]
    save_csv(TARGET_CSV, target_rows)

    physics_rows = [
        {
            "physics_term": "transport_conservation_or_PDE_residual",
            "future_use": "AUTHORIZED_IN_PRINCIPLE",
            "weight": "UNDEFINED",
            "must_be_frozen_before_training": True,
        },
        {
            "physics_term": "injector_boundary_condition",
            "future_use": "AUTHORIZED_IN_PRINCIPLE",
            "weight": "UNDEFINED",
            "must_be_frozen_before_training": True,
        },
        {
            "physics_term": "saturation_bounds",
            "future_use": "AUTHORIZED_IN_PRINCIPLE",
            "weight": "UNDEFINED",
            "must_be_frozen_before_training": True,
        },
        {
            "physics_term": "monotonic_or_front_structure",
            "future_use": "AUTHORIZED_IN_PRINCIPLE",
            "weight": "UNDEFINED",
            "must_be_frozen_before_training": True,
        },
        {
            "physics_term": "mass_conservation",
            "future_use": "AUTHORIZED_IN_PRINCIPLE",
            "weight": "UNDEFINED",
            "must_be_frozen_before_training": True,
        },
    ]
    save_csv(PHYSICS_CSV, physics_rows)

    v15_rows = [
        {
            "scope_item": "SG7E historical reference contract",
            "status": "PRESERVED",
            "times_days": "100,250,500,1000",
            "V16C_supervision_use": "REFERENCE_CONTRACT_ONLY",
        },
        {
            "scope_item": "Certified L2 deployment state",
            "status": "PRESERVED",
            "times_days": "100",
            "V16C_supervision_use": "VALIDATION_REFERENCE_UNTIL_EXACT_MAPPING_PROVEN",
        },
        {
            "scope_item": "SG7D6 frozen deployment artifact",
            "status": "PRESERVED",
            "times_days": "single-state",
            "V16C_supervision_use": "GRID_REFERENCE_ONLY",
        },
        {
            "scope_item": "250/500/1000 frozen deployment states",
            "status": "NOT_CERTIFIED",
            "times_days": "250,500,1000",
            "V16C_supervision_use": "PROHIBITED",
        },
    ]
    save_csv(V15_CSV, v15_rows)

    prohibited_rows = [
        {
            "interpretation": "Use frozen100 directly as a 1078x201 training Y without mapping audit",
            "status": "PROHIBITED",
            "reason": "historical deployment authority does not by itself establish V16C nodewise target identity",
        },
        {
            "interpretation": "Treat SG7D6 grid state as streamline-node truth",
            "status": "PROHIBITED",
            "reason": "grid-level deployment artifact and streamline-node target are different domains",
        },
        {
            "interpretation": "Generate 250/500/1000-day targets from current runtime and call them frozen V15 truth",
            "status": "PROHIBITED",
            "reason": "V15 explicitly did not certify those deployment states",
        },
        {
            "interpretation": "Interpolate/relabel the 100-day state to missing later times",
            "status": "PROHIBITED",
            "reason": "R20R rejected relabelled later-time bindings",
        },
        {
            "interpretation": "Choose target source by lowest numerical error",
            "status": "PROHIBITED",
            "reason": "authority must be provenance/physics based",
        },
        {
            "interpretation": "Fit PI-RNN loss weights in V16C-5",
            "status": "PROHIBITED",
            "reason": "physics-loss contract must be separately frozen before training",
        },
    ]
    save_csv(PROHIBIT_CSV, prohibited_rows)

    handoff_rows = [
        {
            "priority": 1,
            "milestone": "V16C-6",
            "goal": "Audit and bind the source-authentic BL/CCUS transport solver / PI-RNN transport physics that can generate or define streamline-node supervision on frozen Pollock TOF.",
        },
        {
            "priority": 2,
            "milestone": "V16C-7",
            "goal": "Once source physics is bound, define exact Y_transport tensor semantics and any physics-residual supervision terms.",
        },
        {
            "priority": 3,
            "milestone": "LATER",
            "goal": "Train/infer only after input, target, physics-loss, split, and validation contracts are frozen.",
        },
    ]
    save_csv(HANDOFF_CSV, handoff_rows)

    gates = [
        ("V16C4_model_ready_input_status_reproduced", True),
        ("Pollock_TOF_authority_retained", True),
        ("source_authentic_BL_CCUS_transport_named_primary_future_supervision", True),
        ("frozen_V15_100d_state_retained_as_reference_authority", True),
        ("frozen_V15_100d_not_auto_promoted_to_nodewise_Y", True),
        ("SG7D6_retained_as_grid_reference_only", True),
        ("250_500_1000_deployment_targets_prohibited", True),
        ("no_target_selected_by_numerical_performance", True),
        ("physics_supervision_allowed_but_weights_unfrozen", True),
        ("future_target_classes_defined", True),
        ("no_Y_transport_generated", True),
        ("no_transport_solve", True),
        ("no_saturation_generated", True),
        ("no_model_predict", True),
        ("no_training", True),
        ("no_grid_map_back", True),
        ("no_frozen_artifact_mutation", True),
    ]
    save_csv(GATES_CSV, [{"gate": g, "passed": bool(p)} for g, p in gates])

    all_pass = all(bool(p) for _, p in gates)

    if all_pass:
        status = "V16C_TRANSPORT_SUPERVISION_AUTHORITY_CONTRACT_READY"
        diagnosis = (
            "SOURCE_AUTHENTIC_BL_CCUS_STREAMLINE_TRANSPORT_IS_THE_PRIMARY_FUTURE_SUPERVISION_PATH_WHILE_FROZEN_V15_100D_AND_SG7D6_REMAIN_REFERENCE_VALIDATION_AUTHORITIES"
        )
        recommendation = (
            "Freeze this authority contract. Proceed to V16C-6 to audit and bind the existing source-authentic BL/CCUS "
            "transport solver and PI-RNN transport physics onto the frozen Pollock coordinate. Do not generate Y or train yet."
        )
        next_ms = "V16C-6 — Existing BL/CCUS Transport Physics / PI-RNN Lineage Binding Audit"
    else:
        status = "V16C_TRANSPORT_SUPERVISION_AUTHORITY_REQUIRES_AUDIT"
        diagnosis = "ONE_OR_MORE_SUPERVISION_AUTHORITY_GATES_FAILED"
        recommendation = "Audit only failed V16C-5 authority gates."
        next_ms = "V16C-5R — Supervision Authority Residual Audit"

    save_csv(
        DECISION_CSV,
        [{
            "status": status,
            "diagnosis": diagnosis,
            "primary_future_Y_authority": "SOURCE_AUTHENTIC_BL_CCUS_TRANSPORT_ON_POLLOCK_TOF",
            "V15_100d_role": "REFERENCE_VALIDATION_UNTIL_EXACT_MAPPING_AUDIT",
            "SG7D6_role": "GRID_REFERENCE_VALIDATION",
            "later_time_V15_targets": "PROHIBITED",
            "next_milestone": next_ms,
        }],
    )

    contract = {
        "milestone": "V16C-5",
        "status": status,
        "diagnosis": diagnosis,
        "current_target": None,
        "future_primary_supervision": {
            "authority": "source-authentic BL/CCUS transport physics",
            "domain": "frozen Pollock streamline nodes",
            "coordinate": "Pollock TOF",
        },
        "historical_reference_authority": {
            "V15_100d_L2": "preserved reference/validation; not direct Y until exact mapping is proven",
            "SG7D6": "preserved grid-level reference",
            "V15_250_500_1000_deployment": "not certified; prohibited as supervision",
        },
        "physics_supervision": {
            "allowed_in_principle": True,
            "terms": [
                "transport PDE/conservation residual",
                "injector boundary condition",
                "saturation bounds",
                "front/monotonic structure",
                "mass conservation",
            ],
            "weights_frozen": False,
        },
        "constraints": {
            "Y_generated": False,
            "transport_solved": False,
            "training": False,
            "model_predict": False,
            "later_time_state_generated": False,
        },
        "supporting_V15_scope_records_found": [str(p) for p in v15_scope_hits],
        "recommendation": recommendation,
        "next_milestone": next_ms,
    }
    save_json(CONTRACT_JSON, contract)

    save_json(
        SUMMARY_JSON,
        {
            "milestone": "V16C-5",
            "status": status,
            "diagnosis": diagnosis,
            "current_Y_transport": "NOT_GENERATED",
            "primary_future_supervision": "SOURCE_AUTHENTIC_BL_CCUS_TRANSPORT_ON_POLLOCK_TOF",
            "V15_100d_role": "REFERENCE_VALIDATION_ONLY_PENDING_EXACT_MAPPING",
            "SG7D6_role": "GRID_REFERENCE_VALIDATION",
            "later_time_V15_supervision": "PROHIBITED",
            "recommendation": recommendation,
            "next_milestone": next_ms,
        },
    )

    print("SUPERVISION AUTHORITY")
    print("  Primary future Y        : SOURCE-AUTHENTIC BL/CCUS TRANSPORT ON POLLOCK TOF")
    print("  Frozen V15 100-day      : REFERENCE / VALIDATION AUTHORITY")
    print("  SG7D6                    : GRID-LEVEL REFERENCE AUTHORITY")
    print("  250/500/1000 deployment : NOT CERTIFIED / PROHIBITED")
    print("  Y_transport now         : NOT GENERATED")

    print("\nPHYSICS SUPERVISION")
    print("  PDE/conservation        : ALLOWED IN PRINCIPLE / WEIGHT NOT YET FROZEN")
    print("  Boundary conditions     : ALLOWED IN PRINCIPLE / WEIGHT NOT YET FROZEN")
    print("  Bounds/front/mass       : ALLOWED IN PRINCIPLE / WEIGHT NOT YET FROZEN")

    print("\n" + "=" * 78)
    print("V16C-5 FINAL SUPERVISION AUTHORITY GATES")
    print("=" * 78)

    for g, p in gates:
        print(f"[{'PASS' if p else 'FAIL'}] {g}")

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

    print("\nTables:")
    for p in [
        IDENTITY_CSV,
        AUTHORITY_CSV,
        TARGET_CSV,
        PHYSICS_CSV,
        V15_CSV,
        PROHIBIT_CSV,
        HANDOFF_CSV,
        GATES_CSV,
        DECISION_CSV,
    ]:
        print(f"  {p.name}")

    print("\nContract:")
    print(f"  {CONTRACT_JSON.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_JSON.name}")

    print("\n" + "=" * 78)
    print("PAD-STREAM V16C-5 TRANSPORT TARGET / SUPERVISION AUTHORITY CONTRACT: COMPLETE")
    print("=" * 78)


if __name__ == "__main__":
    main()
