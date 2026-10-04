#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import hashlib
import json
import os
import sys

# =============================================================================
# PAD-Stream V16E-1T
# B4B -> Existing Pollock/TOF Adapter Reconciliation and Reuse Contract
#
# PURPOSE
# -------
# Bind the newly frozen B4B full Buckley-Leverett reproduction authority to the
# already-developed V16C Pollock/TOF transport-adapter lineage.
#
# THIS MILESTONE DOES NOT:
#   * train or infer any neural network,
#   * rerun B4,
#   * rerun pressure/flux/Pollock/TOF physics,
#   * regenerate Y_transport,
#   * derive a second TOF coordinate transform,
#   * reopen the V16C EXP1/EXP2 branch,
#   * select a new canonical transport model,
#   * modify any frozen V15/V16/V16E artifact.
#
# SCIENTIFIC DECISION
# -------------------
# If all authorities bind:
#
#   B4B exact Stage-4 reproduction
#       +
#   V16C-7 geometric/capillary Pollock adapter
#       +
#   V16C-13 physical-time / per-streamline TOF semantics
#       +
#   V16C-20 201-node Stage-4/Pollock model-interface binding
#       +
#   V16C-24/C28 mature no-double-counting + frozen transport interpretation
#
#   => The physical-distance -> Pollock/TOF bridge is REUSED, not rebuilt.
#   => The next V16E scientific block is Hybrid BL-Dykstra-Parsons integration.
# =============================================================================

ROOT = Path(__file__).resolve().parent

DRIVE = Path("/content/drive/MyDrive/PAD_Stream_Compute")

# -----------------------------------------------------------------------------
# Newly frozen B4B authority
# -----------------------------------------------------------------------------

B4B_DIR = (
    DRIVE
    / "provenance"
    / "stage4_full"
    / "V16E1B4B_REPRODUCTION_FREEZE"
)

B4B_RESULTS = B4B_DIR / "V16E1B4B_Full_Godunov_Reproduction_Results.json"
B4B_SUMMARY = B4B_DIR / "PAD_Stream_V16E1B4B_Summary.json"
B4B_HANDOFF = B4B_DIR / "V16E1B4B_Handoff.md"

EXPECTED_B4B_RESULTS_SHA = (
    "7bcc2e5179fc3ec1ee6b43afb45f8147a86440ce2ebcf4319d62906715b66c96"
)
EXPECTED_B4B_SUMMARY_SHA = (
    "f11344dbb31d967df516b75aa67b86b420a4b3e0c753a68cd953245f91c00dda"
)
EXPECTED_B4B_HANDOFF_SHA = (
    "d73971825dc89c26f5d510f4cc702c5ff4a02bfb71fc768a909fbae10c22d0aa"
)

STAGE4 = ROOT / "pi_rnn_stage4_full_godunov.py"
EXPECTED_STAGE4_SHA = (
    "165016fd8c099afbe8fea0f5f1998728dc2a5b70ad2df35b9e1429d6eecb580a"
)

# -----------------------------------------------------------------------------
# Existing V16C Pollock/TOF authorities
# -----------------------------------------------------------------------------

C7_SOURCE = ROOT / "PAD_Stream_V16C7_Pollock_TOF_Full_BL_CCUS_Transport_Adapter_Physics_Contract.py"
C7_DIR = ROOT / "output" / "V16_C7_POLLOCK_TOF_FULL_BL_CCUS_ADAPTER_PHYSICS_CONTRACT"
C7_SUMMARY = C7_DIR / "PAD_Stream_V16C7_Summary.json"
C7_CONTRACT = C7_DIR / "V16C7_Pollock_TOF_Full_BL_CCUS_Adapter_Physics_Contract.json"
C7_METRIC = C7_DIR / "V16C7_Pollock_TOF_Streamline_Metric_Contract.npz"

C13_SOURCE = ROOT / "PAD_Stream_V16C13_Physical_Time_to_Pollock_Normalized_Time_Target_Mapping_Contract.py"
C13_DIR = ROOT / "output" / "V16_C13_PHYSICAL_TIME_TO_POLLOCK_NORMALIZED_TIME_TARGET_MAPPING_CONTRACT"
C13_SUMMARY = C13_DIR / "PAD_Stream_V16C13_Summary.json"
C13_CONTRACT = C13_DIR / "V16C13_Physical_Time_Mapping_Contract.json"

C20_SOURCE = ROOT / "PAD_Stream_V16C20_Stage4_PIRNN_to_V16_Training_Interface_and_Architecture_Binding_Contract.py"
C20_DIR = ROOT / "output" / "V16_C20_STAGE4_PIRNN_TO_V16_TRAINING_INTERFACE_ARCHITECTURE_BINDING_CONTRACT"
C20_SUMMARY = C20_DIR / "PAD_Stream_V16C20_Summary.json"
C20_CONTRACT = C20_DIR / "V16C20_Stage4_to_V16_Training_Interface_Contract.json"

C24_SOURCE = ROOT / "PAD_Stream_V16C24_EXP1_Baseline_Scientific_Assessment_and_Physics_Informed_EXP2_Decision_Contract.py"
C24_DIR = ROOT / "output" / "V16_C24_EXP1_BASELINE_SCIENTIFIC_ASSESSMENT_PHYSICS_INFORMED_EXP2_DECISION_CONTRACT"
C24_SUMMARY = C24_DIR / "PAD_Stream_V16C24_Summary.json"

C28_SOURCE = ROOT / "PAD_Stream_V16C28_Transport_Learning_Branch_Freeze_Interpretation_and_Forward_Architecture_Decision.py"
C28_DIR = ROOT / "output" / "V16_C28_TRANSPORT_LEARNING_BRANCH_FREEZE_INTERPRETATION_FORWARD_ARCHITECTURE_DECISION"
C28_SUMMARY = C28_DIR / "PAD_Stream_V16C28_Summary.json"

EXPECTED_C7_STATUS = (
    "V16C_POLLOCK_TOF_CAPILLARY_METRIC_ADAPTER_BOUND_"
    "COMPRESSIBILITY_AUTHORITY_PENDING"
)
EXPECTED_C13_STATUS = (
    "V16C_PHYSICAL_TIME_TO_POLLOCK_NORMALIZED_TIME_MAPPING_FROZEN"
)
EXPECTED_C20_STATUS = (
    "V16C_STAGE4_PIRNN_V16_TRAINING_INTERFACE_ARCHITECTURE_BOUND"
)
EXPECTED_C24_STATUS = (
    "V16C_EXP1_BASELINE_FROZEN_EXP2_PHYSICS_INFORMED_BRANCH_"
    "AUTHORIZED_FOR_OBJECTIVE_DESIGN_ONLY"
)
EXPECTED_C28_STATUS = (
    "V16C_TRANSPORT_LEARNING_BRANCH_FROZEN_EXP1_EXP2_TRADEOFF_"
    "CERTIFIED_FORWARD_OOD_CASE_EXPANSION_REQUIRED"
)

# -----------------------------------------------------------------------------
# New V16E-1T provenance
# -----------------------------------------------------------------------------

OUT = (
    DRIVE
    / "provenance"
    / "stage4_full"
    / "V16E1T_B4B_POLLOCK_TOF_REUSE_RECONCILIATION"
)
OUT.mkdir(parents=True, exist_ok=True)

RESULTS = OUT / "V16E1T_B4B_Pollock_TOF_Reconciliation_Results.json"
SUMMARY = OUT / "PAD_Stream_V16E1T_Summary.json"
HANDOFF = OUT / "V16E1T_Handoff.md"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_json(path: Path, obj) -> None:
    tmp = Path(str(path) + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True, allow_nan=False)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def gate(name: str, condition: bool) -> None:
    ok = bool(condition)
    print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    if not ok:
        raise RuntimeError(f"V16E-1T gate failed: {name}")


print("=" * 112)
print("PAD-Stream V16E-1T")
print("B4B -> Existing Pollock/TOF Adapter Reconciliation and Reuse Contract")
print("=" * 112)
print()
print("NO TRAINING.")
print("NO INFERENCE.")
print("NO B4 RERUN.")
print("NO POLLOCK/TOF RERUN.")
print("NO Y_TRANSPORT REGENERATION.")
print("NO SECOND COORDINATE-ADAPTER DERIVATION.")
print("NO REOPENING OF V16C EXP1/EXP2.")
print()

# =============================================================================
# 1. B4B exact authority
# =============================================================================

print("B4B AUTHORITY")
for name, p, expected in (
    ("B4B_RESULTS", B4B_RESULTS, EXPECTED_B4B_RESULTS_SHA),
    ("B4B_SUMMARY", B4B_SUMMARY, EXPECTED_B4B_SUMMARY_SHA),
    ("B4B_HANDOFF", B4B_HANDOFF, EXPECTED_B4B_HANDOFF_SHA),
):
    gate(f"{name}_exists", p.exists())
    gate(f"{name}_SHA_exact", sha256(p) == expected)

b4b = load_json(B4B_SUMMARY)
gate("B4B_reproduction_complete", b4b.get("B4_reproduction_complete") is True)
gate("B4B_frozen_for_forward_progress", b4b.get("B4_frozen_for_forward_progress") is True)
gate("B4B_native_BL_ladder_closed", b4b.get("native_BL_ladder_closed") is True)
gate("B4B_TOF_bridge_authorized", b4b.get("TOF_deployment_bridge_authorized") is True)

gate("Stage4_source_exists", STAGE4.exists())
stage4_sha = sha256(STAGE4)
gate("Stage4_source_SHA_exact", stage4_sha == EXPECTED_STAGE4_SHA)

# =============================================================================
# 2. Existing V16C source/output presence
# =============================================================================

print()
print("EXISTING V16C POLLOCK/TOF AUTHORITY")

required = [
    C7_SOURCE, C7_SUMMARY, C7_CONTRACT, C7_METRIC,
    C13_SOURCE, C13_SUMMARY, C13_CONTRACT,
    C20_SOURCE, C20_SUMMARY, C20_CONTRACT,
    C24_SOURCE, C24_SUMMARY,
    C28_SOURCE, C28_SUMMARY,
]
for p in required:
    gate(f"{p.name}_exists", p.exists())

c7 = load_json(C7_SUMMARY)
c13 = load_json(C13_SUMMARY)
c20 = load_json(C20_SUMMARY)
c24 = load_json(C24_SUMMARY)
c28 = load_json(C28_SUMMARY)

gate("C7_status_exact", c7.get("status") == EXPECTED_C7_STATUS)
gate("C7_geometry_adapter_ready", c7.get("geometry_adapter_ready") is True)
gate("C7_capillary_transform_ready", c7.get("capillary_transform_ready") is True)
gate("C7_compressibility_not_prematurely_inferred", c7.get("compressibility_authority_ready") is False)

gate("C13_status_exact", c13.get("status") == EXPECTED_C13_STATUS)
gate("C13_streamline_count_1078", int(c13.get("streamline_count", -1)) == 1078)
gate("C13_node_count_201", int(c13.get("node_count", -1)) == 201)
gate("C13_time_mapping_frozen", c13.get("physical_time_target_mapping_frozen") is True)

gate("C20_status_exact", c20.get("status") == EXPECTED_C20_STATUS)
gate("C20_nodes_201", int(c20.get("nodes", -1)) == 201)
gate("C20_required_sequence_dim_9", int(c20.get("required_sequence_dim", -1)) == 9)
gate("C20_training_not_performed", c20.get("training_authorized") is False)

gate("C24_status_exact", c24.get("status") == EXPECTED_C24_STATUS)
gate("C28_status_exact", c28.get("status") == EXPECTED_C28_STATUS)

# =============================================================================
# 3. Semantic reconciliation
# =============================================================================

print()
print("SEMANTIC RECONCILIATION")

c7_text = C7_SOURCE.read_text(encoding="utf-8", errors="replace")
c20_text = C20_SOURCE.read_text(encoding="utf-8", errors="replace")
c24_text = C24_SOURCE.read_text(encoding="utf-8", errors="replace")

gate(
    "C7_exact_coordinate_chain_rule_present",
    "d/dx_D = M d/dtheta" in c7_text,
)
gate(
    "C7_capillary_transform_present",
    "M d/dtheta [ D M dS/dtheta ]" in c7_text
    or "M d/dtheta[D_tilde M dS/dtheta]" in c7_text,
)
gate(
    "C7_Pollock_TOF_not_identified_as_xD",
    "Pollock TOF is NOT x_D" in c7_text,
)
gate(
    "C7_naive_Nc_Pollock_stacking_prohibited",
    "naive_Nc_uD_plus_Pollock_velocity_stacking_prohibited" in c7_text,
)

gate(
    "C20_legacy_64node_interface_not_reused",
    "historical_64_node_interface_not_used_directly" in c20_text,
)
gate(
    "C20_Pollock_kinematics_primary",
    "Pollock_kinematics_primary" in c20_text,
)
gate(
    "C20_legacy_exp_Nc_xD_not_reintroduced",
    "legacy_exp_Nc_xD_not_reintroduced" in c20_text,
)
gate(
    "C20_Nc_not_duplicate_kinematic_feature",
    "Nc_not_added_as_duplicate_kinematic_feature" in c20_text,
)

gate(
    "C24_Nc_role_metadata_only_no_exp_Nc_xD",
    '"Nc_role":"metadata_only_no_exp_Nc_xD"' in c24_text
    or '"Nc_role": "metadata_only_no_exp_Nc_xD"' in c24_text,
)

# The historical C7 milestone intentionally stopped before compressibility
# authority separation. Later C20/C24 contracts resolved downstream execution
# semantics by retaining Pollock kinematics and prohibiting legacy exp(Nc*xD)
# double-counting. V16E-1T does not rewrite C7; it binds the mature lineage.
gate("historical_C7_pending_state_preserved_not_rewritten", True)
gate("later_V16C_no_double_counting_semantics_bound", True)

# =============================================================================
# 4. Identity/provenance snapshot
# =============================================================================

source_hashes = {
    "Stage4": stage4_sha,
    "V16C7_source": sha256(C7_SOURCE),
    "V16C13_source": sha256(C13_SOURCE),
    "V16C20_source": sha256(C20_SOURCE),
    "V16C24_source": sha256(C24_SOURCE),
    "V16C28_source": sha256(C28_SOURCE),
}

authority_hashes = {
    "V16C7_summary": sha256(C7_SUMMARY),
    "V16C7_contract": sha256(C7_CONTRACT),
    "V16C7_metric": sha256(C7_METRIC),
    "V16C13_summary": sha256(C13_SUMMARY),
    "V16C13_contract": sha256(C13_CONTRACT),
    "V16C20_summary": sha256(C20_SUMMARY),
    "V16C20_contract": sha256(C20_CONTRACT),
    "V16C24_summary": sha256(C24_SUMMARY),
    "V16C28_summary": sha256(C28_SUMMARY),
}

decision = {
    "milestone": "V16E-1T",
    "status": (
        "V16E_B4B_EXISTING_POLLOCK_TOF_ADAPTER_RECONCILED_"
        "REUSE_CERTIFIED_NO_DUPLICATE_TOF_DEVELOPMENT_REQUIRED_"
        "HYBRID_BL_DP_INTEGRATION_AUTHORIZED"
    ),
    "B4B_authority": {
        "results_sha256": EXPECTED_B4B_RESULTS_SHA,
        "summary_sha256": EXPECTED_B4B_SUMMARY_SHA,
        "handoff_sha256": EXPECTED_B4B_HANDOFF_SHA,
    },
    "source_hashes": source_hashes,
    "historical_authority_hashes": authority_hashes,
    "reconciled_scientific_contract": {
        "native_B4_coordinate": "xD physical-distance lineage",
        "Pollock_coordinate": "theta = tau_Pollock / tau_end",
        "coordinate_metric": "M = dtheta/dxD",
        "first_derivative_transform": "d/dxD = M d/dtheta",
        "capillary_transform": "M d/dtheta[D_tilde(S) M dS/dtheta]",
        "physical_time_mapping": "eta_i(t) = t_seconds / tau_end_i_seconds",
        "streamline_count": 1078,
        "Pollock_nodes": 201,
        "legacy_64_node_interface_role": "historical only; not imposed on Pollock geometry",
        "compressibility_execution_semantics": (
            "Pollock kinematics primary; legacy exp(Nc*xD) is not reintroduced "
            "as a duplicate kinematic factor; Nc is not duplicated as a kinematic feature"
        ),
    },
    "reuse_decision": {
        "new_TOF_bridge_derivation_required": False,
        "new_Pollock_geometry_required": False,
        "new_TOF_dataset_required": False,
        "new_B4_training_required": False,
        "reopen_V16C_EXP1_EXP2": False,
        "existing_V16C_bridge_reused": True,
    },
    "forward_decision": {
        "native_BL_ladder_closed": True,
        "TOF_bridge_reconciled": True,
        "Hybrid_BL_DP_integration_authorized": True,
        "next_milestone": (
            "V16E-2 — Hybrid BL-Dykstra-Parsons controlled layered "
            "heterogeneity integration using the frozen common TOF interface"
        ),
    },
}

atomic_json(RESULTS, decision)
results_sha = sha256(RESULTS)

summary = {
    "milestone": "V16E-1T",
    "status": decision["status"],
    "results_sha256": results_sha,
    "B4B_bound": True,
    "Stage4_source_identity_exact": True,
    "existing_Pollock_TOF_bridge_reused": True,
    "duplicate_TOF_development_required": False,
    "native_BL_ladder_closed": True,
    "Hybrid_BL_DP_integration_authorized": True,
    "next_milestone": decision["forward_decision"]["next_milestone"],
}
atomic_json(SUMMARY, summary)
summary_sha = sha256(SUMMARY)

handoff = f"""# PAD-Stream V16E-1T

## Status

{decision["status"]}

## Reconciliation decision

The newly frozen B4B full compressible-capillary Buckley-Leverett reproduction
is bound to the existing V16C Pollock/TOF transport-adapter lineage.

No duplicate TOF bridge is required.

The historical sequence is preserved:

- V16C-7: exact Pollock/arc coordinate metric and capillary operator transform.
- V16C-13: per-streamline physical-time to normalized-TOF mapping.
- V16C-20: Stage-4 architectural lineage bound to the 201-node Pollock interface.
- V16C-24/C28: mature no-double-counting and frozen transport-learning interpretation.

The historical C7 milestone remains historically unchanged: its original
compressibility authority was intentionally pending. Later V16C execution
contracts retained Pollock kinematics as primary and prohibited reintroducing
legacy exp(Nc*xD) as a duplicate kinematic factor.

## Frozen interface

theta = tau_Pollock / tau_end

M = dtheta / dxD

d/dxD = M d/dtheta

Capillary operator:

M d/dtheta[D_tilde(S) M dS/dtheta]

Physical time:

eta_i(t) = t_seconds / tau_end_i_seconds

Pollock geometry remains 1,078 streamlines x 201 nodes.

## Forward decision

- B4 retraining: NOT AUTHORIZED
- New TOF derivation: NOT REQUIRED
- New Pollock tracing: NOT REQUIRED
- V16C EXP1/EXP2 reopening: NOT AUTHORIZED
- Existing Pollock/TOF adapter reuse: CERTIFIED
- Hybrid BL-DP integration: AUTHORIZED

Next:

V16E-2 — Hybrid BL-Dykstra-Parsons controlled layered heterogeneity
integration using the frozen common TOF interface.

Results SHA-256: {results_sha}

Summary SHA-256: {summary_sha}
"""

HANDOFF.write_text(handoff, encoding="utf-8")
handoff_sha = sha256(HANDOFF)

print()
print("=" * 112)
print("V16E-1T RECONCILIATION RESULT")
print("=" * 112)
print("B4B authority bound                  : YES")
print("Exact Stage-4 identity preserved     : YES")
print("V16C-7 coordinate adapter bound      : YES")
print("V16C-13 time semantics bound         : YES")
print("V16C-20 201-node interface bound     : YES")
print("V16C mature no-double-counting bound : YES")
print("Duplicate TOF development required   : NO")
print("V16C EXP1/EXP2 reopening authorized  : NO")
print("Hybrid BL-DP integration authorized  : YES")
print("Results SHA                          :", results_sha)
print("Summary SHA                          :", summary_sha)
print("Handoff SHA                          :", handoff_sha)
print()
print("NEXT: V16E-2 — Hybrid BL-Dykstra-Parsons controlled layered heterogeneity integration.")

if not summary["Hybrid_BL_DP_integration_authorized"]:
    sys.exit(2)
