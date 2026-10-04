#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import hashlib
import json
import os
import runpy
import sys

import numpy as np

# =============================================================================
# PAD-Stream V16E-2
# Controlled 8-Layer Dykstra-Parsons Physics Reproduction
# and Prospective Hybrid BL-DP Integration Contract
#
# PURPOSE
# -------
# Close the exact classical DP benchmark before any new learned Hybrid model is
# trained. This is a NEW V16E prospective integration milestone.
#
# It DOES:
#   * bind the frozen B4B -> Pollock/TOF reconciliation authority,
#   * bind the exact recovered 8-layer DP physics source,
#   * reproduce the canonical 8-layer DP algebra directly from that source,
#   * verify layer-flow allocation, pore-volume clocks, breakthrough ordering,
#     aggregation, and heterogeneity diagnostics,
#   * freeze the common TOF/DP interface for a future prospective Hybrid model.
#
# It DOES NOT:
#   * claim recovery of the historical Hybrid DP PI-RNN/layer-RNN,
#   * train a neural network,
#   * infer with a neural network,
#   * alter B4, Pollock, TOF, pressure, Darcy flux, or map-back authorities,
#   * reopen V16C EXP1/EXP2,
#   * reuse geology0029 as unseen test evidence.
# =============================================================================

ROOT = Path(__file__).resolve().parent
DRIVE = Path("/content/drive/MyDrive/PAD_Stream_Compute")

# -----------------------------------------------------------------------------
# Frozen V16E-1T-R2 authority
# -----------------------------------------------------------------------------

T2_DIR = (
    DRIVE
    / "provenance"
    / "stage4_full"
    / "V16E1T_R2_B4B_POLLOCK_TOF_AUTHORITY_CHAIN_RECONCILIATION"
)

T2_RESULTS = T2_DIR / "V16E1T_R2_B4B_Pollock_TOF_Authority_Chain_Reconciliation_Results.json"
T2_SUMMARY = T2_DIR / "PAD_Stream_V16E1T_R2_Summary.json"
T2_HANDOFF = T2_DIR / "V16E1T_R2_Handoff.md"

EXPECTED_T2_RESULTS_SHA = "c29566e1d4c284d6402228ffd65ba5b831efff9d28168f1d1cc8365cc9b41d7b"
EXPECTED_T2_SUMMARY_SHA = "82e8d50877617f250b107b3b1e8cef3c0c524cb177452f4c554ee0dca7279a68"
EXPECTED_T2_HANDOFF_SHA = "fd88c494b75aefcef6651e992598441c66663136e17dd5a0dd9fd38a30c6a94f"

# -----------------------------------------------------------------------------
# Exact recovered DP authority
# -----------------------------------------------------------------------------

DP_SOURCE = ROOT / "PAD_Stream_CCUS_Physics_Development_v14_Complete_Validation.py"
EXPECTED_DP_SOURCE_SHA = "45c3c8a26ff270df8d28dc6e67ed432a3de86255229f7046f5b0f3d1899d27f6"

# Canonical eight-layer table preserved in scenario_validate_dp().
K_MD = np.array([174., 103., 487., 100., 141., 904., 1223., 160.], dtype=float)
H_FT = np.array([50., 48., 54., 44., 42., 48., 50., 40.], dtype=float)
PHI = np.array([0.22, 0.18, 0.21, 0.15, 0.20, 0.21, 0.20, 0.20], dtype=float)
SWC = np.array([0.37, 0.41, 0.35, 0.42, 0.39, 0.34, 0.32, 0.42], dtype=float)
KRO_MAX = np.array([0.40, 0.45, 0.55, 0.70, 0.30, 0.65, 0.80, 0.60], dtype=float)
KRW_MAX = np.array([0.05, 0.15, 0.20, 0.33, 0.20, 0.30, 0.40, 0.17], dtype=float)

SOR = 0.20
MU_W = 0.5
MU_O = 0.7

PVI_GRID = np.linspace(0.0, 1.5, 61, dtype=float)

# -----------------------------------------------------------------------------
# New provenance
# -----------------------------------------------------------------------------

OUT = (
    DRIVE
    / "provenance"
    / "hybrid_dp"
    / "V16E2_CONTROLLED_8LAYER_DP_REPRODUCTION_AND_HYBRID_INTEGRATION_CONTRACT"
)
OUT.mkdir(parents=True, exist_ok=True)

RESULTS = OUT / "V16E2_Controlled_8Layer_DP_Reproduction_Results.json"
SUMMARY = OUT / "PAD_Stream_V16E2_Summary.json"
HANDOFF = OUT / "V16E2_Handoff.md"
NPZ = OUT / "V16E2_8Layer_DP_Benchmark.npz"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
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
        raise RuntimeError(f"V16E-2 gate failed: {name}")


print("=" * 118)
print("PAD-Stream V16E-2")
print("Controlled 8-Layer Dykstra-Parsons Physics Reproduction + Prospective Hybrid Integration Contract")
print("=" * 118)
print()
print("NO TRAINING.")
print("NO MODEL INFERENCE.")
print("NO HISTORICAL HYBRID CHECKPOINT CLAIM.")
print("NO B4/POLLOCK/TOF/PRESSURE/FLUX RERUN.")
print("NO V16C EXP1/EXP2 REOPENING.")
print()

# =============================================================================
# 1. Bind prior authority
# =============================================================================

print("V16E-1T-R2 AUTHORITY")
for name, p, expected in (
    ("V16E1T_R2_RESULTS", T2_RESULTS, EXPECTED_T2_RESULTS_SHA),
    ("V16E1T_R2_SUMMARY", T2_SUMMARY, EXPECTED_T2_SUMMARY_SHA),
    ("V16E1T_R2_HANDOFF", T2_HANDOFF, EXPECTED_T2_HANDOFF_SHA),
):
    gate(f"{name}_exists", p.exists())
    gate(f"{name}_SHA_exact", sha256(p) == expected)

t2 = load_json(T2_SUMMARY)
gate(
    "Hybrid_BL_DP_integration_authorized_by_T2",
    t2.get("Hybrid_BL_DP_integration_authorized") is True,
)
gate(
    "duplicate_TOF_development_not_required",
    t2.get("duplicate_TOF_development_required") is False,
)

# =============================================================================
# 2. Bind exact DP source
# =============================================================================

print()
print("EXACT DP SOURCE AUTHORITY")
gate("DP_source_exists", DP_SOURCE.exists())
gate("DP_source_SHA_exact", sha256(DP_SOURCE) == EXPECTED_DP_SOURCE_SHA)

src_text = DP_SOURCE.read_text(encoding="utf-8", errors="replace")

for marker in (
    "class DykstraParsons",
    'allocation="kh"',
    'allocation="kh_mob"',
    "full DP table",
    "8-layer",
    "layered_flow_storage",
    "dykstra_parsons_coefficient",
):
    gate(f"DP_source_marker_{marker}", marker.lower() in src_text.lower())

# Import as a module namespace without executing __main__.
ns = runpy.run_path(str(DP_SOURCE), run_name="__v16e2_dp_authority__")

DykstraParsons = ns["DykstraParsons"]
layered_flow_storage = ns["layered_flow_storage"]
dykstra_parsons_coefficient = ns["dykstra_parsons_coefficient"]

# =============================================================================
# 3. Reproduce canonical eight-layer DP physics
# =============================================================================

print()
print("CANONICAL 8-LAYER DP REPRODUCTION")

dp_kh = DykstraParsons(
    K_MD, H_FT, PHI, SWC, SOR, KRW_MAX, KRO_MAX, MU_W, MU_O, "kh"
)

dp_mob = DykstraParsons(
    K_MD, H_FT, PHI, SWC, SOR, KRW_MAX, KRO_MAX, MU_W, MU_O, "kh_mob"
)

rec_kh, wc_kh = dp_kh.run(PVI_GRID)
rec_mob, wc_mob = dp_mob.run(PVI_GRID)

F_kh = np.asarray(dp_kh.F, dtype=float)
F_mob = np.asarray(dp_mob.F, dtype=float)
PV = np.asarray(dp_kh.PV, dtype=float)
movable = np.asarray(dp_kh.movable, dtype=float)
Ri = np.asarray(dp_kh.Ri, dtype=float)
tau_bt = np.array([float(layer.tau_bt) for layer in dp_kh.layers], dtype=float)

local_pvi = (
    F_kh[:, None]
    * (float(PV.sum()) / PV[:, None])
    * PVI_GRID[None, :]
)

order = np.argsort(Ri)[::-1]

Fcap, Phicap, lorenz = layered_flow_storage(K_MD, H_FT, PHI)
dp_coeff = float(dykstra_parsons_coefficient(K_MD))

gate("layer_count_8", len(K_MD) == 8)
gate("all_input_arrays_length_8", all(len(x) == 8 for x in (H_FT, PHI, SWC, KRO_MAX, KRW_MAX)))
gate("permeability_positive", np.all(K_MD > 0))
gate("thickness_positive", np.all(H_FT > 0))
gate("porosity_positive", np.all(PHI > 0))
gate("saturation_span_positive", np.all(1.0 - SWC - SOR > 0))

gate("kh_rate_fractions_finite", np.all(np.isfinite(F_kh)))
gate("kh_mob_rate_fractions_finite", np.all(np.isfinite(F_mob)))
gate("kh_rate_fractions_positive", np.all(F_kh > 0))
gate("kh_mob_rate_fractions_positive", np.all(F_mob > 0))
gate("kh_rate_fractions_sum_one", abs(float(F_kh.sum()) - 1.0) <= 1e-12)
gate("kh_mob_rate_fractions_sum_one", abs(float(F_mob.sum()) - 1.0) <= 1e-12)

gate("pore_volume_positive", np.all(PV > 0))
gate("movable_pore_volume_positive", np.all(movable > 0))
gate("local_PVI_finite", np.all(np.isfinite(local_pvi)))
gate("local_PVI_nonnegative", np.all(local_pvi >= 0))

gate("breakthrough_times_finite", np.all(np.isfinite(tau_bt)))
gate("breakthrough_times_positive", np.all(tau_bt > 0))
gate("speed_indices_finite", np.all(np.isfinite(Ri)))
gate("speed_indices_positive", np.all(Ri > 0))

for name, a in (
    ("rec_kh", rec_kh),
    ("wc_kh", wc_kh),
    ("rec_kh_mob", rec_mob),
    ("wc_kh_mob", wc_mob),
):
    gate(f"{name}_finite", np.all(np.isfinite(a)))

gate("recovery_kh_bounded", np.min(rec_kh) >= -1e-12 and np.max(rec_kh) <= 1.0 + 1e-12)
gate("recovery_kh_mob_bounded", np.min(rec_mob) >= -1e-12 and np.max(rec_mob) <= 1.0 + 1e-12)
gate("watercut_kh_bounded", np.min(wc_kh) >= -1e-12 and np.max(wc_kh) <= 1.0 + 1e-12)
gate("watercut_kh_mob_bounded", np.min(wc_mob) >= -1e-12 and np.max(wc_mob) <= 1.0 + 1e-12)

gate("recovery_kh_monotone", np.all(np.diff(rec_kh) >= -1e-10))
gate("recovery_kh_mob_monotone", np.all(np.diff(rec_mob) >= -1e-10))

gate("DP_coefficient_finite", np.isfinite(dp_coeff))
gate("DP_coefficient_physical_range", 0.0 <= dp_coeff <= 1.0)
gate("Lorenz_coefficient_finite", np.isfinite(lorenz))
gate("Lorenz_coefficient_physical_range", -1e-12 <= lorenz <= 1.0 + 1e-12)

# Physics identities used by the prospective Hybrid branch.
expected_F_kh = (K_MD * H_FT) / np.sum(K_MD * H_FT)
gate("kh_allocation_exact_identity", np.max(np.abs(F_kh - expected_F_kh)) <= 1e-14)

expected_F_mob = (
    K_MD * H_FT * KRO_MAX / MU_O
) / np.sum(K_MD * H_FT * KRO_MAX / MU_O)
gate("kh_mob_allocation_exact_identity", np.max(np.abs(F_mob - expected_F_mob)) <= 1e-14)

expected_PV = PHI * H_FT
gate("PV_exact_identity", np.max(np.abs(PV - expected_PV)) <= 1e-14)

expected_Ri = K_MD / (PHI * (1.0 - SWC - SOR))
gate("speed_index_exact_identity", np.max(np.abs(Ri - expected_Ri)) <= 1e-12)

# Save deterministic benchmark arrays.
np.savez_compressed(
    NPZ,
    k_mD=K_MD,
    h_ft=H_FT,
    phi=PHI,
    swc=SWC,
    sor=np.array([SOR], dtype=float),
    krw_max=KRW_MAX,
    kro_max=KRO_MAX,
    pvi_total=PVI_GRID,
    F_kh=F_kh,
    F_kh_mob=F_mob,
    PV=PV,
    movable_PV=movable,
    local_PVI_kh=local_pvi,
    speed_index_Ri=Ri,
    breakthrough_tau_local=tau_bt,
    breakthrough_order_fast_to_slow=order.astype(np.int64),
    recovery_kh=np.asarray(rec_kh, dtype=float),
    watercut_kh=np.asarray(wc_kh, dtype=float),
    recovery_kh_mob=np.asarray(rec_mob, dtype=float),
    watercut_kh_mob=np.asarray(wc_mob, dtype=float),
    flow_capacity=np.asarray(Fcap, dtype=float),
    storage_capacity=np.asarray(Phicap, dtype=float),
    dykstra_parsons_coefficient=np.array([dp_coeff], dtype=float),
    lorenz_coefficient=np.array([lorenz], dtype=float),
)

gate("benchmark_npz_written", NPZ.exists())

# =============================================================================
# 4. Freeze prospective Hybrid integration semantics
# =============================================================================

hybrid_contract = {
    "historical_Hybrid_DP_checkpoint_status": "UNAVAILABLE_FOR_EXACT_PROVENANCE",
    "new_model_identity_required": True,
    "model_label_if_trained": "NEW_V16E_PROSPECTIVE_HYBRID_BL_DP",
    "teacher": "EXACT_RECOVERED_8_LAYER_DYKSTRA_PARSONS_PHYSICS_PLUS_FROZEN_B4_TOF_TRANSPORT_AUTHORITY",
    "layer_inputs": [
        "layer_id",
        "k_mD",
        "h_ft",
        "phi",
        "swc",
        "sor",
        "krw_max",
        "kro_max",
        "layer_rate_fraction",
        "layer_pore_volume",
        "local_PVI",
        "speed_index_Ri",
        "breakthrough_tau_local",
    ],
    "shared_transport_coordinate": "total-flow TOF / normalized Pollock theta",
    "heterogeneity_roles": {
        "Dykstra_Parsons": "controlled layered allocation and aggregation benchmark",
        "F_Phi_Lorenz": "dynamic flow/storage heterogeneity descriptor",
        "SGSim": "later full spatial stochastic geology/connectivity authority",
    },
    "required_outputs": [
        "layer_saturation_or_response",
        "layer_breakthrough_state",
        "aggregate_recovery_or_storage",
        "flux_weighted_producer_fractional_flow",
        "inventory_closure_diagnostic",
    ],
    "acceptance_rules": [
        "sum(layer_rate_fraction) == 1",
        "local PVI follows F_l * (PV_total/PV_l) * PVI_total",
        "breakthrough ordering must agree with exact DP teacher",
        "aggregate producer response must use flux weighting",
        "recovery/storage aggregation must use physically appropriate pore-volume weighting",
        "learned output remains proposal until physics/inventory acceptance",
        "conservative path-to-grid map-back remains final accepted grid-state authority",
    ],
    "training_authorized_now": False,
    "next_required_action": (
        "Freeze one prospective Hybrid model/training protocol with new experiment identity "
        "before any training."
    ),
}

results = {
    "milestone": "V16E-2",
    "status": (
        "V16E_CONTROLLED_8LAYER_DP_PHYSICS_REPRODUCED_"
        "PROSPECTIVE_HYBRID_BL_DP_INTERFACE_FROZEN_"
        "TRAINING_PROTOCOL_DESIGN_AUTHORIZED_TRAINING_NOT_YET_AUTHORIZED"
    ),
    "V16E1T_R2_authority": {
        "results_sha256": EXPECTED_T2_RESULTS_SHA,
        "summary_sha256": EXPECTED_T2_SUMMARY_SHA,
        "handoff_sha256": EXPECTED_T2_HANDOFF_SHA,
    },
    "DP_source_sha256": EXPECTED_DP_SOURCE_SHA,
    "benchmark_npz_sha256": sha256(NPZ),
    "canonical_8_layer_table": {
        "k_mD": K_MD.tolist(),
        "h_ft": H_FT.tolist(),
        "phi": PHI.tolist(),
        "swc": SWC.tolist(),
        "sor": SOR,
        "krw_max": KRW_MAX.tolist(),
        "kro_max": KRO_MAX.tolist(),
        "mu_w_cP": MU_W,
        "mu_o_cP": MU_O,
    },
    "benchmark_metrics": {
        "DP_coefficient": dp_coeff,
        "Lorenz_coefficient": float(lorenz),
        "final_recovery_kh": float(rec_kh[-1]),
        "final_watercut_kh": float(wc_kh[-1]),
        "final_recovery_kh_mob": float(rec_mob[-1]),
        "final_watercut_kh_mob": float(wc_mob[-1]),
        "fast_to_slow_layer_indices_zero_based": order.astype(int).tolist(),
        "fast_to_slow_layer_numbers_one_based": (order + 1).astype(int).tolist(),
        "local_breakthrough_tau": tau_bt.tolist(),
    },
    "prospective_Hybrid_contract": hybrid_contract,
    "historical_Hybrid_recovered": False,
    "historical_Hybrid_claim_authorized": False,
    "new_prospective_Hybrid_design_authorized": True,
    "training_authorized": False,
    "next_milestone": (
        "V16E-2P — Prospective Hybrid BL-DP model/training protocol freeze "
        "(single protocol; new experiment identity; no historical-checkpoint claim)"
    ),
}

atomic_json(RESULTS, results)
results_sha = sha256(RESULTS)

summary = {
    "milestone": "V16E-2",
    "status": results["status"],
    "results_sha256": results_sha,
    "benchmark_npz_sha256": results["benchmark_npz_sha256"],
    "DP_source_exact": True,
    "canonical_8_layer_DP_reproduced": True,
    "Hybrid_interface_frozen": True,
    "historical_Hybrid_recovered": False,
    "new_prospective_Hybrid_design_authorized": True,
    "training_authorized": False,
    "next_milestone": results["next_milestone"],
}

atomic_json(SUMMARY, summary)
summary_sha = sha256(SUMMARY)

HANDOFF.write_text(
    f"""# PAD-Stream V16E-2

## Status

{results["status"]}

## Exact physics authority

Canonical recovered 8-layer DP source SHA-256:

`{EXPECTED_DP_SOURCE_SHA}`

Benchmark NPZ SHA-256:

`{results["benchmark_npz_sha256"]}`

## Canonical 8-layer benchmark

Dykstra-Parsons coefficient: `{dp_coeff:.12g}`

Streamline-native layered Lorenz coefficient: `{lorenz:.12g}`

Fast-to-slow layer order (1-based):

`{(order + 1).astype(int).tolist()}`

Final recovery at 1.5 total PVI:
- kh allocation: `{rec_kh[-1]:.12g}`
- kh*endpoint-mobility allocation: `{rec_mob[-1]:.12g}`

## Provenance boundary

The historical Hybrid DP PI-RNN/layer-RNN is not recovered.

Any learned Hybrid built next must be a NEW V16E prospective model with a new
experiment identity, new checkpoint SHA, and frozen protocol.

## Forward decision

Prospective Hybrid BL-DP protocol design: AUTHORIZED

Training now: NOT AUTHORIZED

Next:
V16E-2P — freeze the single prospective Hybrid model/training protocol.

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
print("Exact 8-layer DP source bound              : YES")
print("Canonical 8-layer DP physics reproduced    : YES")
print("kh / kh-mob allocations conservative       : YES")
print("Local PVI identity reproduced              : YES")
print("Breakthrough ordering authority reproduced : YES")
print("DP coefficient / Lorenz diagnostics bound  : YES")
print("Historical Hybrid checkpoint recovered     : NO")
print("Historical Hybrid claim authorized         : NO")
print("New prospective Hybrid design authorized   : YES")
print("Training authorized now                    : NO")
print("Benchmark NPZ SHA                          :", sha256(NPZ))
print("Results SHA                                :", results_sha)
print("Summary SHA                                :", summary_sha)
print("Handoff SHA                                :", handoff_sha)
print()
print("NEXT: V16E-2P — freeze one prospective Hybrid BL-DP model/training protocol.")
