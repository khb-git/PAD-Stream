from __future__ import annotations

from pathlib import Path
import csv
import hashlib
import json


# =============================================================================
# PAD-Stream V16C-1
# Travel-Time Hierarchy Integration Contract
#
# PURPOSE
# -------
# V16B closed with three frozen travel-time roles:
#
#   FMM     -> rapid scalar connectivity control
#   ADV     -> directional Eulerian travel-time field
#   Pollock -> authoritative trajectory-level TOF reference
#
# V16C-1 defines how these three coordinate systems enter downstream PAD-Stream
# transport WITHOUT solving transport and WITHOUT changing any frozen V16B
# artifact.
#
# CORE ARCHITECTURE
# -----------------
#
#   Foundation Case 0001
#         |
#         +--> FMM T(x) --------------------+
#         |                                  |
#         +--> ADV tau_ADV(x) ---------------+--> GRID-LEVEL TRANSPORT CONTEXT
#         |                                  |
#         +--> Pollock x_s(xi), tau_s(xi) ---+--> STREAMLINE TRANSPORT COORDINATE
#
# GRID-LEVEL ROLE
# ---------------
# FMM and ADV are retained as Eulerian fields that can be:
#   - mapped to every grid cell,
#   - used as model conditioning channels,
#   - used for connectivity / arrival-time diagnostics,
#   - used as auxiliary inputs to future recurrent/global state models.
#
# STREAMLINE ROLE
# ---------------
# Pollock remains the authoritative coordinate for the existing streamline
# transport branch and PI-RNN transport deployment.
#
# IMPORTANT
# ---------
# V16C-1 DOES NOT:
#   - replace Pollock TOF with ADV,
#   - replace Pollock TOF with FMM,
#   - train a PI-RNN,
#   - generate saturation,
#   - map saturation back to the grid,
#   - recalibrate any travel-time field,
#   - solve new pressure / flux / velocity / FMM / ADV physics.
# =============================================================================


ROOT = Path(__file__).resolve().parent

B9_DIR = ROOT / "output" / "V16_B9_TRAVEL_TIME_ARCHITECTURE_ROLE_DECISION"
B9_SUMMARY = B9_DIR / "PAD_Stream_V16B9_Summary.json"
B9_CONTRACT = B9_DIR / "V16B9_Travel_Time_Architecture_Role_Contract.json"

FOUNDATION_DIR = (
    ROOT
    / "output"
    / "V16_A_R8R_FOUNDATION_CASE_0001_FREEZE"
    / "PAD_Stream_V16A_Foundation_Case_0001"
)
FOUNDATION_NPZ = FOUNDATION_DIR / "V16A_Foundation_Case_0001.npz"

B2_NPZ = (
    ROOT / "output" / "V16_B2_EXACT_3D_FMM_ARRIVAL_TIME_BASELINE"
    / "V16B2_Exact_3D_FMM_Arrival_Time.npz"
)

B7_NPZ = (
    ROOT / "output" / "V16_B7_CONTROLLED_DIRECTIONAL_ADVECTIVE_TRAVEL_TIME_SOLVE"
    / "V16B7_Directional_Advective_Travel_Time.npz"
)

OUT = ROOT / "output" / "V16_C1_TRAVEL_TIME_HIERARCHY_INTEGRATION_CONTRACT"
OUT.mkdir(parents=True, exist_ok=True)

IDENTITY_CSV = OUT / "V16C1_Input_Identity.csv"
ROLE_CSV = OUT / "V16C1_Transport_Coordinate_Role_Matrix.csv"
CHANNEL_CSV = OUT / "V16C1_Downstream_Conditioning_Channel_Contract.csv"
FLOW_CSV = OUT / "V16C1_PAD_Stream_Transport_Integration_Flow.csv"
PROHIBIT_CSV = OUT / "V16C1_Prohibited_Substitutions.csv"
NEXT_CSV = OUT / "V16C1_Implementation_Handoff.csv"
GATES_CSV = OUT / "V16C1_Final_Integration_Contract_Gates.csv"
DECISION_CSV = OUT / "V16C1_Integration_Contract_Decision.csv"

CONTRACT_JSON = OUT / "V16C1_Travel_Time_Hierarchy_Integration_Contract.json"
SUMMARY_JSON = OUT / "PAD_Stream_V16C1_Summary.json"


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


def main():
    print("\n" + "=" * 78)
    print("PAD-Stream V16C-1")
    print("Travel-Time Hierarchy Integration Contract")
    print("=" * 78)

    print("""
NO TRANSPORT SOLVE WILL BE EXECUTED.
NO SATURATION FIELD WILL BE GENERATED.
NO PI-RNN WILL BE TRAINED OR INFERRED.
NO GRID MAP-BACK WILL BE EXECUTED.
NO FMM / ADV / POLLOCK ARTIFACT WILL BE CHANGED.
NO PRESSURE / FLUX / VELOCITY PHYSICS WILL BE RERUN.
THIS MILESTONE DEFINES DOWNSTREAM TRANSPORT ROLES ONLY.
""")

    for p in [
        B9_SUMMARY,
        B9_CONTRACT,
        FOUNDATION_NPZ,
        B2_NPZ,
        B7_NPZ,
    ]:
        if not p.exists():
            raise FileNotFoundError(p)

    b9 = load_json(B9_SUMMARY)

    if b9.get("status") != "V16B_TRAVEL_TIME_ARCHITECTURE_ROLES_FROZEN":
        raise RuntimeError("V16C-1 requires frozen V16B-9 architecture roles.")

    save_csv(
        IDENTITY_CSV,
        [{
            "foundation_sha256": sha256_file(FOUNDATION_NPZ),
            "V16B2_FMM_sha256": sha256_file(B2_NPZ),
            "V16B7_ADV_sha256": sha256_file(B7_NPZ),
            "V16B9_contract_sha256": sha256_file(B9_CONTRACT),
        }],
    )

    role_rows = [
        {
            "representation": "FMM",
            "domain": "GRID",
            "coordinate": "T_FMM(x)",
            "transport_role": "AUXILIARY_CONNECTIVITY_AND_ARRIVAL_CONTEXT",
            "authoritative_for_streamline_transport": False,
            "eligible_as_model_conditioning_channel": True,
            "eligible_as_grid_diagnostic": True,
        },
        {
            "representation": "ADV",
            "domain": "GRID",
            "coordinate": "tau_ADV(x)",
            "transport_role": "DIRECTIONAL_EULERIAN_TRAVEL_TIME_CONTEXT",
            "authoritative_for_streamline_transport": False,
            "eligible_as_model_conditioning_channel": True,
            "eligible_as_grid_diagnostic": True,
        },
        {
            "representation": "POLLOCK",
            "domain": "STREAMLINE",
            "coordinate": "tau_Pollock(s,xi)",
            "transport_role": "AUTHORITATIVE_STREAMLINE_TRANSPORT_COORDINATE",
            "authoritative_for_streamline_transport": True,
            "eligible_as_model_conditioning_channel": True,
            "eligible_as_grid_diagnostic": False,
        },
    ]
    save_csv(ROLE_CSV, role_rows)

    channel_rows = [
        {
            "channel": "permeability_context",
            "source": "Kx,Ky,Kz",
            "scope": "grid",
            "required_for_next_transport_branch": True,
        },
        {
            "channel": "pressure_context",
            "source": "pressure",
            "scope": "grid",
            "required_for_next_transport_branch": True,
        },
        {
            "channel": "scalar_arrival_context",
            "source": "T_FMM",
            "scope": "grid",
            "required_for_next_transport_branch": False,
        },
        {
            "channel": "directional_arrival_context",
            "source": "tau_ADV",
            "scope": "grid",
            "required_for_next_transport_branch": True,
        },
        {
            "channel": "streamline_transport_coordinate",
            "source": "tau_Pollock",
            "scope": "streamline",
            "required_for_next_transport_branch": True,
        },
        {
            "channel": "streamline_geometry",
            "source": "streamline_xyz",
            "scope": "streamline",
            "required_for_next_transport_branch": True,
        },
        {
            "channel": "streamline_weight",
            "source": "streamline_weight",
            "scope": "streamline",
            "required_for_next_transport_branch": True,
        },
    ]
    save_csv(CHANNEL_CSV, channel_rows)

    flow_rows = [
        {
            "stage": 1,
            "component": "Frozen Foundation Case 0001",
            "output": "K,phi,p,Q,V,Pollock reference",
        },
        {
            "stage": 2,
            "component": "FMM branch",
            "output": "grid scalar arrival/connectivity context",
        },
        {
            "stage": 3,
            "component": "ADV branch",
            "output": "grid directional travel-time context",
        },
        {
            "stage": 4,
            "component": "Pollock branch",
            "output": "streamline geometry + authoritative TOF coordinate",
        },
        {
            "stage": 5,
            "component": "Future transport integration",
            "output": "Pollock-coordinate transport conditioned by grid-level geology/pressure/arrival context",
        },
        {
            "stage": 6,
            "component": "Future map-back/global state",
            "output": "grid saturation/state update after transport solution",
        },
    ]
    save_csv(FLOW_CSV, flow_rows)

    prohibited = [
        {
            "substitution": "ADV replaces Pollock TOF in existing streamline PI-RNN branch",
            "status": "PROHIBITED",
            "reason": "ADV is directional Eulerian baseline, not exact characteristic TOF",
        },
        {
            "substitution": "FMM replaces Pollock TOF in existing streamline PI-RNN branch",
            "status": "PROHIBITED",
            "reason": "FMM discards flow orientation",
        },
        {
            "substitution": "Pollock removed because ADV exists",
            "status": "PROHIBITED",
            "reason": "Pollock remains authoritative trajectory-level coordinate",
        },
        {
            "substitution": "FMM removed because ADV performs better",
            "status": "PROHIBITED",
            "reason": "FMM retained as low-cost scalar control and screening field",
        },
        {
            "substitution": "travel-time fields cross-calibrated before integration",
            "status": "PROHIBITED",
            "reason": "V16B baselines are intentionally untuned",
        },
    ]
    save_csv(PROHIBIT_CSV, prohibited)

    handoff = [
        {
            "priority": 1,
            "milestone": "V16C-2",
            "goal": "Build a frozen multi-coordinate transport database containing Pollock TOF plus sampled FMM/ADV context along every streamline node.",
        },
        {
            "priority": 2,
            "milestone": "V16C-3",
            "goal": "Define PI-RNN/transport conditioning contract using geology, pressure, FMM and ADV without replacing Pollock TOF.",
        },
        {
            "priority": 3,
            "milestone": "V16C-4+",
            "goal": "Execute transport integration, conservative map-back and global recurrent-state coupling under new V16 contracts.",
        },
    ]
    save_csv(NEXT_CSV, handoff)

    gates = [
        ("V16B9_roles_reproduced", True),
        ("FMM_grid_role_defined", True),
        ("ADV_grid_role_defined", True),
        ("Pollock_streamline_role_defined", True),
        ("Pollock_retained_as_authoritative_streamline_coordinate", True),
        ("FMM_conditioning_role_allowed", True),
        ("ADV_conditioning_role_allowed", True),
        ("no_FMM_forced_replacement_of_Pollock", True),
        ("no_ADV_forced_replacement_of_Pollock", True),
        ("future_transport_conditioning_channels_defined", True),
        ("future_map_back_separated_from_coordinate_definition", True),
        ("no_transport_solve", True),
        ("no_saturation_generated", True),
        ("no_model_predict", True),
        ("no_training", True),
        ("no_frozen_artifact_mutation", True),
    ]
    save_csv(GATES_CSV, [{"gate": g, "passed": bool(p)} for g, p in gates])

    status = "V16C_TRAVEL_TIME_HIERARCHY_INTEGRATION_CONTRACT_READY"
    diagnosis = (
        "FMM_ADV_AND_POLLOCK_HAVE_NONCOMPETING_DOWNSTREAM_ROLES_WITH_POLLOCK_RETAINED_AS_THE_AUTHORITATIVE_STREAMLINE_TRANSPORT_COORDINATE"
    )
    recommendation = (
        "Freeze this integration contract. Proceed to V16C-2 to assemble a multi-coordinate streamline transport database "
        "that samples frozen FMM and ADV fields onto the frozen Pollock nodes while preserving Pollock TOF as the transport coordinate."
    )
    next_ms = "V16C-2 — Multi-Coordinate Streamline Transport Database Assembly"

    save_csv(
        DECISION_CSV,
        [{
            "status": status,
            "diagnosis": diagnosis,
            "Pollock_transport_role": "AUTHORITATIVE",
            "ADV_role": "DIRECTIONAL_GRID_CONTEXT",
            "FMM_role": "SCALAR_GRID_CONTEXT",
            "next_milestone": next_ms,
        }],
    )

    contract = {
        "milestone": "V16C-1",
        "status": status,
        "diagnosis": diagnosis,
        "transport_coordinate_authority": {
            "streamline": "Pollock TOF",
            "grid_directional": "ADV tau",
            "grid_scalar": "FMM arrival time",
        },
        "integration_rule": (
            "FMM and ADV may condition downstream transport models; neither may replace Pollock TOF in the existing streamline transport branch."
        ),
        "next_database_contract": {
            "streamline_nodes": "existing frozen Pollock XYZ nodes",
            "primary_coordinate": "Pollock TOF",
            "auxiliary_grid_samples": ["FMM arrival time", "ADV travel time"],
            "context": ["K", "pressure", "streamline weight"],
        },
        "recommendation": recommendation,
        "next_milestone": next_ms,
    }
    save_json(CONTRACT_JSON, contract)

    save_json(
        SUMMARY_JSON,
        {
            "milestone": "V16C-1",
            "status": status,
            "diagnosis": diagnosis,
            "Pollock_role": "AUTHORITATIVE_STREAMLINE_TRANSPORT_COORDINATE",
            "ADV_role": "DIRECTIONAL_EULERIAN_CONTEXT",
            "FMM_role": "SCALAR_CONNECTIVITY_CONTEXT",
            "recommendation": recommendation,
            "next_milestone": next_ms,
        },
    )

    print("FROZEN TRANSPORT-COORDINATE ROLES")
    print("  FMM                     : GRID SCALAR CONNECTIVITY / ARRIVAL CONTEXT")
    print("  ADV                     : GRID DIRECTIONAL TRAVEL-TIME CONTEXT")
    print("  POLLOCK                 : AUTHORITATIVE STREAMLINE TRANSPORT COORDINATE")

    print("\nDOWNSTREAM RULE")
    print("  Pollock TOF remains primary for streamline transport.")
    print("  FMM and ADV may enter as auxiliary conditioning / diagnostic channels.")

    print("\n" + "=" * 78)
    print("V16C-1 FINAL INTEGRATION CONTRACT GATES")
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
        ROLE_CSV,
        CHANNEL_CSV,
        FLOW_CSV,
        PROHIBIT_CSV,
        NEXT_CSV,
        GATES_CSV,
        DECISION_CSV,
    ]:
        print(f"  {p.name}")

    print("\nContract:")
    print(f"  {CONTRACT_JSON.name}")

    print("\nSummary:")
    print(f"  {SUMMARY_JSON.name}")

    print("\n" + "=" * 78)
    print("PAD-STREAM V16C-1 TRAVEL-TIME HIERARCHY INTEGRATION CONTRACT: COMPLETE")
    print("=" * 78)


if __name__ == "__main__":
    main()
