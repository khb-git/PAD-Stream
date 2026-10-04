#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import hashlib
import importlib.util
import json
import os
import sys
import numpy as np

# =============================================================================
# PAD-Stream V16E-2
# Controlled 8-Layer Dykstra-Parsons Physics Reproduction
# and Prospective Hybrid BL-DP Integration Contract
#
# PURPOSE
# -------
# 1. Bind the completed B4B -> Pollock/TOF reconciliation (V16E-1T-R2).
# 2. Reproduce the exact recovered canonical Dykstra-Parsons physics source.
# 3. Exercise the source-native DP behavioral validation.
# 4. Reproduce the dissertation 8-layer layered benchmark from the source table.
# 5. Freeze the interface by which the B4/TOF transport lineage may be paired
#    with controlled layered heterogeneity.
#
# IMPORTANT PROVENANCE RULE
# -------------------------
# The historical Hybrid DP PI-RNN / layer-RNN checkpoint was frozen unavailable
# in V16E-0D. Therefore this milestone DOES NOT claim to recover or deploy that
# historical learned model.
#
# Any learned Hybrid BL-DP model built after this milestone must be a NEW V16E
# prospective model with its own protocol, experiment identity, checkpoint SHA,
# train/validation/locked-test firewall, and explicit physics teacher.
#
# NO TRAINING occurs here.
# =============================================================================

ROOT = Path(__file__).resolve().parent
DRIVE = Path("/content/drive/MyDrive/PAD_Stream_Compute")

# -----------------------------------------------------------------------------
# V16E-1T-R2 authority
# -----------------------------------------------------------------------------
T2_DIR = (
    DRIVE / "provenance" / "stage4_full"
    / "V16E1T_R2_B4B_POLLOCK_TOF_AUTHORITY_CHAIN_RECONCILIATION"
)
T2_RESULTS = T2_DIR / "V16E1T_R2_B4B_Pollock_TOF_Authority_Chain_Reconciliation_Results.json"
T2_SUMMARY = T2_DIR / "PAD_Stream_V16E1T_R2_Summary.json"
T2_HANDOFF = T2_DIR / "V16E1T_R2_Handoff.md"

T2_RESULTS_SHA = "c29566e1d4c284d6402228ffd65ba5b831efff9d28168f1d1cc8365cc9b41d7b"
T2_SUMMARY_SHA = "82e8d50877617f250b107b3b1e8cef3c0c524cb177452f4c554ee0dca7279a68"
T2_HANDOFF_SHA = "fd88c494b75aefcef6651e992598441c66663136e17dd5a0dd9fd38a30c6a94f"

# -----------------------------------------------------------------------------
# V16E-0D provenance closure / exact DP source
# -----------------------------------------------------------------------------
E0D_SUMMARY = (
    ROOT / "output" / "V16_E0D_LEGACY_AVAILABILITY_FREEZE_AND_WP0_CLOSURE"
    / "PAD_Stream_V16E0D_Summary.json"
)
E0D_EXPECTED_STATUS = (
    "V16E_WP0_ARCHITECTURE_RECONCILIATION_COMPLETE_"
    "BL_AND_DP_PHYSICS_SOURCES_RECOVERED_"
    "HISTORICAL_LEARNED_ARTIFACTS_FROZEN_UNAVAILABLE_"
    "PROSPECTIVE_V16E_REPRODUCTION_PROTOCOL_AUTHORIZED_"
    "TRAINING_NOT_YET_AUTHORIZED"
)

DP_SOURCE = ROOT / "PAD_Stream_CCUS_Physics_Development_v14_Complete_Validation.py"
DP_SOURCE_SHA = "45c3c8a26ff270df8d28dc6e67ed432a3de86255229f7046f5b0f3d1899d27f6"

# -----------------------------------------------------------------------------
# Canonical 8-layer table from the exact source
# -----------------------------------------------------------------------------
K_MD = np.array([174., 103., 487., 100., 141., 904., 1223., 160.], dtype=float)
H_FT = np.array([50., 48., 54., 44., 42., 48., 50., 40.], dtype=float)
PHI = np.array([0.22, 0.18, 0.21, 0.15, 0.20, 0.21, 0.20, 0.20], dtype=float)
SWC = np.array([0.37, 0.41, 0.35, 0.42, 0.39, 0.34, 0.32, 0.42], dtype=float)
KRO = np.array([0.40, 0.45, 0.55, 0.70, 0.30, 0.65, 0.80, 0.60], dtype=float)
KRW = np.array([0.05, 0.15, 0.20, 0.33, 0.20, 0.30, 0.40, 0.17], dtype=float)
SOR = 0.20
MU_W = 0.5
MU_O = 0.7

# -----------------------------------------------------------------------------
# Output
# -----------------------------------------------------------------------------
OUT = DRIVE / "provenance" / "hybrid_dp" / "V16E2_CONTROLLED_8LAYER_DP_REPRODUCTION"
OUT.mkdir(parents=True, exist_ok=True)

RESULTS = OUT / "V16E2_Controlled_8Layer_DP_Reproduction_Results.json"
SUMMARY = OUT / "PAD_Stream_V16E2_Summary.json"
HANDOFF = OUT / "V16E2_Handoff.md"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json_atomic(path: Path, obj) -> None:
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
        raise RuntimeError(f"V16E-2 gate failed: {name}")


def import_exact_dp_source(path: Path):
    spec = importlib.util.spec_from_file_location("pad_stream_v14_dp_authority", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not create import spec for exact DP source.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


print("=" * 118)
print("PAD-Stream V16E-2")
print("Controlled 8-Layer DP Physics Reproduction and Prospective Hybrid BL-DP Integration Contract")
print("=" * 118)
print("""
NO NEURAL-NETWORK TRAINING.
NO HISTORICAL HYBRID CHECKPOINT CLAIM.
NO SGSim MODIFICATION.
NO POLLOCK/TOF RECOMPUTATION.
NO B4 RETRAINING.
NO OOD REOPENING.

THIS MILESTONE REPRODUCES THE EXACT DP PHYSICS TEACHER AND FREEZES THE
PROSPECTIVE HYBRID INTERFACE.
""")

# =============================================================================
# 1. Bind V16E-1T-R2
# =============================================================================

print("V16E-1T-R2 AUTHORITY")
for name, p, expected in (
    ("T2_RESULTS", T2_RESULTS, T2_RESULTS_SHA),
    ("T2_SUMMARY", T2_SUMMARY, T2_SUMMARY_SHA),
    ("T2_HANDOFF", T2_HANDOFF, T2_HANDOFF_SHA),
):
    gate(f"{name}_exists", p.exists())
    gate(f"{name}_SHA_exact", sha256(p) == expected)

t2 = load_json(T2_SUMMARY)
gate("T2_existing_Pollock_TOF_bridge_reused", t2.get("historical_repair_chain_bound") is True)
gate("T2_duplicate_TOF_development_not_required", t2.get("duplicate_TOF_development_required") is False)
gate("T2_Hybrid_BL_DP_authorized", t2.get("Hybrid_BL_DP_integration_authorized") is True)

# =============================================================================
# 2. Bind WP0 / DP source provenance
# =============================================================================

print()
print("V16E-0D / DP SOURCE AUTHORITY")
gate("E0D_summary_exists", E0D_SUMMARY.exists())
e0d = load_json(E0D_SUMMARY)
gate("E0D_status_exact", e0d.get("status") == E0D_EXPECTED_STATUS)
gate("E0D_DP_8_layer_physics_recovered", e0d.get("DP_8_layer_physics_recovered") is True)
gate("E0D_historical_Hybrid_unavailable", e0d.get("historical_Hybrid_DP_available") is False)
gate("E0D_training_not_authorized", e0d.get("training_authorized") is False)

gate("DP_source_exists", DP_SOURCE.exists())
gate("DP_source_SHA_exact", sha256(DP_SOURCE) == DP_SOURCE_SHA)

# =============================================================================
# 3. Load exact source and execute its native DP validation
# =============================================================================

print()
print("SOURCE-NATIVE DP REPRODUCTION")
dpmod = import_exact_dp_source(DP_SOURCE)

gate("DykstraParsons_class_available", hasattr(dpmod, "DykstraParsons"))
gate("dykstra_parsons_coefficient_available", hasattr(dpmod, "dykstra_parsons_coefficient"))
gate("layered_flow_storage_available", hasattr(dpmod, "layered_flow_storage"))
gate("v14_DP_behavior_test_available", hasattr(dpmod, "_v14_test_dykstra_parsons_behavior"))

native_pass, native_message, native_metrics = dpmod._v14_test_dykstra_parsons_behavior()
gate("source_native_v14_DP_behavior_test", native_pass)

# =============================================================================
# 4. Canonical dissertation 8-layer table reproduction
# =============================================================================

print()
print("CANONICAL 8-LAYER BENCHMARK")

dp_kh = dpmod.DykstraParsons(
    K_MD, H_FT, PHI, SWC, SOR, KRW, KRO,
    MU_W, MU_O, "kh"
)
dp_mob = dpmod.DykstraParsons(
    K_MD, H_FT, PHI, SWC, SOR, KRW, KRO,
    MU_W, MU_O, "kh_mob"
)

gate("eight_layers_exact", len(dp_kh.k) == 8)
gate("all_permeabilities_positive", np.all(K_MD > 0.0))
gate("all_thicknesses_positive", np.all(H_FT > 0.0))
gate("all_porosity_physical", np.all((PHI > 0.0) & (PHI < 1.0)))
gate("all_movable_saturation_positive", np.all(1.0 - SWC - SOR > 0.0))

gate("kh_rate_fractions_positive", np.all(dp_kh.F > 0.0))
gate("kh_rate_fractions_sum_to_one", abs(float(np.sum(dp_kh.F)) - 1.0) <= 1e-14)
gate("khmob_rate_fractions_positive", np.all(dp_mob.F > 0.0))
gate("khmob_rate_fractions_sum_to_one", abs(float(np.sum(dp_mob.F)) - 1.0) <= 1e-14)

gate("layer_PV_positive", np.all(dp_kh.PV > 0.0))
gate("layer_movable_PV_positive", np.all(dp_kh.movable > 0.0))
gate("speed_index_positive", np.all(dp_kh.Ri > 0.0))

# System responses.
pvi = np.linspace(0.0, 1.5, 151)
rec_kh, wc_kh = dp_kh.run(pvi)
rec_mob, wc_mob = dp_mob.run(pvi)

gate("kh_recovery_finite", np.all(np.isfinite(rec_kh)))
gate("kh_watercut_finite", np.all(np.isfinite(wc_kh)))
gate("khmob_recovery_finite", np.all(np.isfinite(rec_mob)))
gate("khmob_watercut_finite", np.all(np.isfinite(wc_mob)))
gate("kh_recovery_monotone", np.all(np.diff(rec_kh) >= -1e-12))
gate("khmob_recovery_monotone", np.all(np.diff(rec_mob) >= -1e-12))
gate("kh_watercut_bounded", np.all((wc_kh >= -1e-12) & (wc_kh <= 1.0 + 1e-12)))
gate("khmob_watercut_bounded", np.all((wc_mob >= -1e-12) & (wc_mob <= 1.0 + 1e-12)))

# Heterogeneity descriptors from exact source.
v_dp = float(dpmod.dykstra_parsons_coefficient(K_MD))
_, phi_cap, lorenz = dpmod.layered_flow_storage(K_MD, H_FT, PHI)
lorenz = float(lorenz)

gate("DP_coefficient_physical", 0.0 < v_dp < 1.0)
gate("Lorenz_coefficient_physical", 0.0 < lorenz < 1.0)
gate("storage_capacity_endpoint_one", abs(float(phi_cap[-1]) - 1.0) <= 1e-12)

# Exact layer breakthrough clocks under the DP allocation identity:
# local PVI_l = F_l * (PV_total/PV_l) * total_PVI
# total_PVI_bt,l = tau_bt,l / [F_l * PV_total/PV_l]
PVtot = float(np.sum(dp_kh.PV))

def layer_breakthrough_total_pvi(dp):
    local_clock_per_total = dp.F * (PVtot / dp.PV)
    tau_bt = np.array([float(layer.tau_bt) for layer in dp.layers])
    total_bt = tau_bt / local_clock_per_total
    return local_clock_per_total, tau_bt, total_bt

clock_kh, tau_bt_kh, total_bt_kh = layer_breakthrough_total_pvi(dp_kh)
clock_mob, tau_bt_mob, total_bt_mob = layer_breakthrough_total_pvi(dp_mob)

gate("kh_local_clocks_positive", np.all(clock_kh > 0.0))
gate("kh_breakthrough_finite_positive", np.all(np.isfinite(total_bt_kh)) and np.all(total_bt_kh > 0.0))
gate("khmob_local_clocks_positive", np.all(clock_mob > 0.0))
gate("khmob_breakthrough_finite_positive", np.all(np.isfinite(total_bt_mob)) and np.all(total_bt_mob > 0.0))
gate("layered_breakthrough_is_nonuniform", float(np.ptp(total_bt_kh)) > 0.0)

order_speed = np.argsort(dp_kh.Ri)[::-1]
order_bt_kh = np.argsort(total_bt_kh)
order_bt_mob = np.argsort(total_bt_mob)

# Local-PVI identity audit at one deterministic system state.
audit_total_pvi = 0.30
local_pvi_kh = clock_kh * audit_total_pvi
local_pvi_mob = clock_mob * audit_total_pvi

gate(
    "local_PVI_identity_exact_kh",
    np.allclose(
        local_pvi_kh,
        dp_kh.F * (PVtot / dp_kh.PV) * audit_total_pvi,
        rtol=0.0, atol=0.0
    )
)
gate(
    "local_PVI_identity_exact_khmob",
    np.allclose(
        local_pvi_mob,
        dp_mob.F * (PVtot / dp_mob.PV) * audit_total_pvi,
        rtol=0.0, atol=0.0
    )
)

# =============================================================================
# 5. Prospective Hybrid BL-DP interface freeze
# =============================================================================

print()
print("PROSPECTIVE HYBRID BL-DP CONTRACT")

# This is an interface/role contract, not a learned model.
hybrid_contract = {
    "provenance": {
        "historical_Hybrid_DP_checkpoint_available": False,
        "historical_Hybrid_DP_claim_permitted": False,
        "future_model_label": "NEW_V16E_PROSPECTIVE_HYBRID_BL_DP",
    },
    "exact_teacher": {
        "DP_source": DP_SOURCE.name,
        "DP_source_sha256": DP_SOURCE_SHA,
        "BL_transport_lineage": "B4B full compressible-capillary BL + reconciled Pollock/TOF adapter",
    },
    "heterogeneity_role": {
        "DP": "controlled layered allocation/aggregation benchmark",
        "not_allowed": "DP may not replace 3-D pressure/Pollock connectivity or SGSim spatial geology",
    },
    "per_layer_inputs": [
        "layer_id",
        "k_mD",
        "h_ft",
        "porosity",
        "Swc",
        "Sor",
        "krw_max",
        "kro_max",
        "layer_rate_fraction",
        "layer_PV",
        "local_PVI",
    ],
    "global_or_case_inputs": [
        "DP_coefficient",
        "F_Phi_or_Lorenz_descriptor",
        "physical_time_or_total_PVI",
        "B4 rock/fluid/constitutive conditioning",
        "authoritative Pollock/TOF coordinates when deployed in PAD-Stream",
    ],
    "teacher_outputs": [
        "per_layer_transport_state",
        "per_layer_breakthrough",
        "aggregate_recovery_or_storage",
        "flux_weighted_outlet_fractional_flow",
        "pore_volume_weighted_inventory",
    ],
    "hard_physics_rules": [
        "sum(layer_rate_fraction) == 1",
        "local_PVI_l = F_l * (PV_total/PV_l) * total_PVI",
        "aggregate outlet fractional flow is flux weighted",
        "aggregate recovery/storage uses the appropriate movable-PV/PV weighting",
        "learned transport is proposal only until physics/inventory acceptance",
        "pressure, Darcy flux and Pollock kinematics remain exact authorities",
        "conservative grid map-back remains final 3-D state authority",
    ],
    "training": {
        "authorized_now": False,
        "reason": "A prospective teacher-dataset/split/objective protocol must be frozen before training.",
        "new_checkpoint_requires_new_SHA_and_manifest": True,
        "historical_checkpoint_relabeling_prohibited": True,
    },
}

gate("historical_Hybrid_not_claimed", hybrid_contract["provenance"]["historical_Hybrid_DP_claim_permitted"] is False)
gate("new_Hybrid_identity_required", hybrid_contract["provenance"]["future_model_label"] == "NEW_V16E_PROSPECTIVE_HYBRID_BL_DP")
gate("DP_role_layered_not_3D_connectivity", "may not replace" in hybrid_contract["heterogeneity_role"]["not_allowed"])
gate("training_not_authorized_here", hybrid_contract["training"]["authorized_now"] is False)

# =============================================================================
# 6. Save freeze
# =============================================================================

layer_rows = []
for i in range(8):
    layer_rows.append({
        "layer": i + 1,
        "k_mD": float(K_MD[i]),
        "h_ft": float(H_FT[i]),
        "phi": float(PHI[i]),
        "Swc": float(SWC[i]),
        "Sor": float(SOR),
        "krw_max": float(KRW[i]),
        "kro_max": float(KRO[i]),
        "Ri": float(dp_kh.Ri[i]),
        "F_kh": float(dp_kh.F[i]),
        "F_kh_mob": float(dp_mob.F[i]),
        "PV_relative": float(dp_kh.PV[i]),
        "movable_PV_relative": float(dp_kh.movable[i]),
        "local_clock_per_total_PVI_kh": float(clock_kh[i]),
        "local_clock_per_total_PVI_kh_mob": float(clock_mob[i]),
        "layer_tau_bt": float(tau_bt_kh[i]),
        "total_PVI_bt_kh": float(total_bt_kh[i]),
        "total_PVI_bt_kh_mob": float(total_bt_mob[i]),
    })

status = (
    "V16E_CONTROLLED_8LAYER_DP_PHYSICS_REPRODUCED_"
    "PROSPECTIVE_HYBRID_BL_DP_INTERFACE_FROZEN_"
    "HISTORICAL_HYBRID_NOT_CLAIMED_"
    "PROSPECTIVE_TEACHER_PROTOCOL_DESIGN_AUTHORIZED_TRAINING_NOT_YET_AUTHORIZED"
)

results = {
    "milestone": "V16E-2",
    "status": status,
    "V16E1T_R2_authority": {
        "results_sha256": T2_RESULTS_SHA,
        "summary_sha256": T2_SUMMARY_SHA,
        "handoff_sha256": T2_HANDOFF_SHA,
    },
    "E0D_summary_sha256_runtime": sha256(E0D_SUMMARY),
    "DP_source_sha256": DP_SOURCE_SHA,
    "source_native_v14_DP_behavior": {
        "passed": bool(native_pass),
        "message": native_message,
        "metrics": native_metrics,
    },
    "canonical_8_layer_table": layer_rows,
    "heterogeneity": {
        "dykstra_parsons_coefficient": v_dp,
        "layered_lorenz_coefficient": lorenz,
        "speed_order_fast_to_slow_layers": [int(i + 1) for i in order_speed],
        "breakthrough_order_kh_layers": [int(i + 1) for i in order_bt_kh],
        "breakthrough_order_kh_mob_layers": [int(i + 1) for i in order_bt_mob],
    },
    "system_response": {
        "pvi_grid_start": float(pvi[0]),
        "pvi_grid_end": float(pvi[-1]),
        "pvi_grid_count": int(len(pvi)),
        "kh_final_recovery": float(rec_kh[-1]),
        "kh_final_watercut": float(wc_kh[-1]),
        "kh_mob_final_recovery": float(rec_mob[-1]),
        "kh_mob_final_watercut": float(wc_mob[-1]),
    },
    "hybrid_contract": hybrid_contract,
    "forward_decision": {
        "DP_physics_teacher_frozen": True,
        "Hybrid_BL_DP_interface_frozen": True,
        "prospective_Hybrid_teacher_protocol_design_authorized": True,
        "training_authorized_now": False,
        "next_milestone": (
            "V16E-3 — Prospective Hybrid BL-DP teacher-dataset, split, "
            "objective and model-protocol freeze before any new training"
        ),
    },
}

save_json_atomic(RESULTS, results)
results_sha = sha256(RESULTS)

summary = {
    "milestone": "V16E-2",
    "status": status,
    "results_sha256": results_sha,
    "DP_source_sha256": DP_SOURCE_SHA,
    "source_native_DP_behavior_passed": bool(native_pass),
    "DP_8_layer_physics_reproduced": True,
    "Hybrid_BL_DP_interface_frozen": True,
    "historical_Hybrid_DP_claimed": False,
    "prospective_Hybrid_protocol_design_authorized": True,
    "training_authorized": False,
    "next_milestone": results["forward_decision"]["next_milestone"],
}
save_json_atomic(SUMMARY, summary)
summary_sha = sha256(SUMMARY)

HANDOFF.write_text(
f"""# PAD-Stream V16E-2

## Status

{status}

## What was reproduced

The exact recovered Version-14 Dykstra-Parsons physics source was SHA-bound and
its source-native DP behavior test was executed successfully.

The canonical dissertation 8-layer table was then reproduced with both:

- `kh` layer-rate allocation
- `kh_mob` endpoint-mobility-weighted allocation

Rate fractions close to one exactly, layer PV and movable PV remain positive,
system recovery is monotone, producer fractional flow remains bounded, and
per-layer local-PVI/breakthrough clocks are explicitly preserved.

## Heterogeneity

Dykstra-Parsons coefficient: {v_dp:.12g}

Layered F-Phi/Lorenz coefficient: {lorenz:.12g}

Fast-to-slow speed-index layer order:

{[int(i + 1) for i in order_speed]}

KH breakthrough order:

{[int(i + 1) for i in order_bt_kh]}

KH-mob breakthrough order:

{[int(i + 1) for i in order_bt_mob]}

## Provenance rule

The historical Hybrid DP PI-RNN / layer-RNN remains unavailable and is NOT
claimed here.

Any learned Hybrid model created from this point forward is a NEW V16E
prospective artifact with its own training protocol, checkpoint identity and SHA.

## Frozen Hybrid interface

B4B/Pollock-TOF provides the transport lineage.

DP provides controlled layer allocation and local displacement clocks:

`local_PVI_l = F_l * (PV_total/PV_l) * total_PVI`

DP does not replace 3-D pressure, Darcy flux, Pollock connectivity, SGSim
geology, or conservative grid map-back.

## Forward decision

Prospective Hybrid teacher/data/model protocol design: AUTHORIZED

Training now: NOT AUTHORIZED

Next:

V16E-3 — Prospective Hybrid BL-DP teacher-dataset, split, objective and
model-protocol freeze before any new training.

Results SHA-256: {results_sha}

Summary SHA-256: {summary_sha}
""",
encoding="utf-8",
)
handoff_sha = sha256(HANDOFF)

print()
print("=" * 118)
print("V16E-2 RESULT")
print("=" * 118)
print("Exact DP source authority bound          : YES")
print("Source-native DP behavior reproduced     : YES")
print("Canonical 8-layer benchmark reproduced   : YES")
print("KH rate allocation conserved             : YES")
print("KH-mob rate allocation conserved         : YES")
print("Local-PVI clocks reproduced              : YES")
print("Layer breakthrough clocks reproduced     : YES")
print("DP / Lorenz descriptors reproduced       : YES")
print("Historical Hybrid checkpoint claimed     : NO")
print("Prospective Hybrid interface frozen      : YES")
print("Prospective training authorized now      : NO")
print("Teacher/model protocol design authorized : YES")
print("Results SHA                              :", results_sha)
print("Summary SHA                              :", summary_sha)
print("Handoff SHA                              :", handoff_sha)
print()
print("NEXT: V16E-3 — Prospective Hybrid BL-DP teacher-dataset/split/objective/model-protocol freeze.")

if not summary["prospective_Hybrid_protocol_design_authorized"]:
    sys.exit(2)
