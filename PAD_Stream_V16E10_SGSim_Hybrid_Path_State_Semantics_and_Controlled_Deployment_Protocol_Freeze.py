#!/usr/bin/env python3
"""PAD-Stream V16E-10
SGSim Hybrid Path-State Semantics and Controlled Deployment Protocol Freeze.

Scientific purpose
------------------
V16E-9-R1 certified the unchanged Hybrid10/Hybrid12 checkpoints and the
Pollock-to-fan adapter on homogeneous/local states with screened exact fallback.
V16E-10 prospectively freezes how those already accepted components may be used
on the heterogeneous SGSim dissertation base without silently homogenizing
path-varying constitutive properties or double-counting heterogeneity already
represented by pressure / Darcy / Pollock / TOF physics.

This milestone performs NO neural inference and NO SGSim deployment.  It does
not load or mutate any Version-15 numerical state.  It freezes the semantics and
safety gates that the first controlled SGSim streamline pilot must obey.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

MILESTONE = "V16E-10"
SUCCESS = "V16E10_SGSIM_HYBRID_PATH_STATE_SEMANTICS_AND_CONTROLLED_DEPLOYMENT_PROTOCOL_FROZEN"
BLOCKED = "V16E10_SGSIM_HYBRID_PATH_STATE_PROTOCOL_FREEZE_BLOCKED"
NEXT_PASS = "V16E-11 — SGSim 100-Day Path-State Eligibility Audit and Controlled Hybrid Streamline Pilot"
NEXT_FAIL = "V16E-10-R1 — SGSim path-state protocol repair; deployment remains locked"

E9R1_REL = Path("provenance/hybrid_dp/V16E9_R1_RECONCILED_ADAPTER_IDENTICAL_STATE_CERTIFICATION")
E8R1_REL = Path("provenance/hybrid_dp/V16E8_R1_ADAPTER_PHYSICS_SCREEN_RECONCILIATION_PROTOCOL")
E7_REL = Path("provenance/hybrid_dp/V16E7_HYBRID_EVIDENCE_AND_DEPLOYMENT_ROLE_FREEZE")
E3_REL = Path("provenance/hybrid_dp/V16E3_R1_HYBRID_PROTOCOL_FREEZE")
OUT_REL = Path("provenance/hybrid_dp/V16E10_SGSIM_HYBRID_PATH_STATE_PROTOCOL_FREEZE")

E9R1_RUNNER = (
    "PAD_Stream_V16E9_R1_Reconciled_Hybrid_Transport_Adapter_Identical_State_Certification.py",
    "c5dbf87fb17d16cced65f1e77941e6d8e8e274b8a24f852136ac210d0c732ff0",
)
E9R1 = {
    "audit": (
        "V16E9_R1_Reconciled_Identical_State_Certification_Audit.json",
        "59e5c40c29c67b56ed5b900f6f52b71912e0e91a6900f732507be56afd34a2e5",
    ),
    "summary": (
        "PAD_Stream_V16E9_R1_Summary.json",
        "17a2bf9db9f9085934e73e26065f881d687945ec62d10b33e5756091d12cc40e",
    ),
    "handoff": (
        "V16E9_R1_Handoff.md",
        "5aefc455441e0c13288c593865ffddc1e649ad59804635221fb2c5ae739a0b49",
    ),
}
E8R1 = {
    "contract": (
        "V16E8_R1_Adapter_Physics_Screen_Reconciliation_Protocol.json",
        "4c00180b966cf2e21b3774d1df4c06520f03ba6a4354815c0bfb895d02187cb0",
    ),
    "results": (
        "V16E8_R1_Adapter_Physics_Screen_Reconciliation_Results.json",
        "0e29a43b240f6b94e9c2fbaa9c56fbaab5b0824712f21132b003851f473938ea",
    ),
}
E7_ROUTING = (
    "V16E7_Deployment_Routing_Contract.json",
    "88d434ecc292c49b7cff58aa70223e76a2dc2ce6f8f7124c461867274407fcea",
)
E3_PROTOCOL = (
    "V16E3_R1_Hybrid_BL_DP_Protocol.json",
    "57bcb2e74c68eb77ed8de69d75ddafc00b38d2f3c4e9b884bfc87676160db4a1",
)
V16C1_SOURCE = (
    "PAD_Stream_V16C1_Travel_Time_Hierarchy_Integration_Contract.py",
    "c52971034547162eb1376de83975ac8ee7aa9872d7fe790eda281d7b566ebf29",
)

# Source files used only as frozen-lineage context.  Their current repository
# SHA values are recorded in the E10 output; E10 does not rewrite or execute them.
SGSIM_CONTEXT_SOURCES = [
    "PAD_Stream_V15SG1_SGSim_Geology_Integration.py",
    "PAD_Stream_V15SG5_Exact_Pollock_Streamlines.py",
    "PAD_Stream_V15SG6_TOF_Transport_Coordinates.py",
    "PAD_Stream_V15SG7A_Full_Physics_TOF_Transport.py",
]

FEATURES10 = ["no", "nw", "swc", "sor", "mu_w", "mu_o", "phi", "tD", "xD_star", "Sw_star"]
FEATURES12 = ["no", "nw", "swc", "sor", "mu_w", "mu_o", "phi", "krw_max", "kro_max", "tD", "xD_star", "Sw_star"]
EXPECTED_BOUNDS = {
    "no": [2.0, 4.0],
    "nw": [2.0, 4.0],
    "swc": [0.20, 0.45],
    "sor": [0.10, 0.30],
    "mu_w_cP": [0.30, 1.0],
    "mu_o_cP": [0.50, 5.0],
    "phi": [0.15, 0.25],
    "k_mD": [50.0, 1250.0],
    "h_ft": [20.0, 60.0],
    "krw_max_Hybrid12": [0.05, 0.80],
    "kro_max_Hybrid12": [0.30, 0.80],
}

PROHIBITIONS = [
    "NO TRAINING, GRADIENT UPDATE, OR CHECKPOINT CREATION.",
    "NO MODEL INFERENCE OR CHECKPOINT LOAD.",
    "NO INTERNAL-TEST RE-EVALUATION OR OOD REOPENING.",
    "NO SGSim PRESSURE / DARCY / POLLOCK / TOF RECOMPUTATION.",
    "NO SGSim SATURATION PREDICTION OR GRID MAP-BACK.",
    "NO CHANGE TO HYBRID10 / HYBRID12 CHECKPOINTS OR V16E-7 ROUTING.",
    "NO DP KH REALLOCATION ON TOP OF EXACT 3-D POLLOCK FLOW WEIGHTS.",
    "NO ABSOLUTE PERMEABILITY OR LAYER THICKNESS NEURAL INPUT CHANNEL.",
    "NO PATHWISE AVERAGING / HOMOGENIZATION OF PHI OR CONSTITUTIVE ENDPOINTS.",
    "NO SILENT 0.8/0.8 ENDPOINT ASSUMPTION WHEN ENDPOINT METADATA IS ABSENT.",
    "NO NEAREST-CELL PROPERTY GUESS FROM RESAMPLED XYZ WHEN EXACT POLLOCK CELL PROVENANCE IS UNAVAILABLE.",
    "NO POST-BREAKTHROUGH HYBRID USE AND NO FULL COMPRESSIBLE-CAPILLARY EQUIVALENCE CLAIM.",
]


class GateError(RuntimeError):
    pass


class Gates:
    def __init__(self):
        self.items = {}

    def check(self, name: str, condition, detail=""):
        ok = bool(condition)
        self.items[name] = {"passed": ok, "detail": detail}
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f": {detail}" if detail else ""), flush=True)
        if not ok:
            raise GateError(name + (f": {detail}" if detail else ""))


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encoded(obj) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def bind(g: Gates, label: str, path: Path, expected: str):
    g.check(label + "_exists", path.is_file(), str(path))
    actual = sha(path)
    g.check(label + "_SHA_exact", actual == expected, actual if actual != expected else "")
    return actual


def publish(out: Path, payloads: dict[str, bytes]):
    if out.exists():
        if not out.is_dir() or set(p.name for p in out.iterdir() if p.is_file()) != set(payloads):
            raise GateError("Existing E10 output directory differs; nothing overwritten")
        for name, data in payloads.items():
            if (out / name).read_bytes() != data:
                raise GateError("Existing E10 output bytes differ; nothing overwritten")
        print("Existing identical V16E-10 freeze reused.", flush=True)
        return

    out.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".v16e10-", dir=out.parent))
    try:
        for name, data in payloads.items():
            p = stage / name
            with p.open("xb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
        stage.rename(out)
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def run(project: Path, drive: Path, out: Path) -> int:
    print("=" * 126)
    print("PAD-Stream V16E-10 SGSim Hybrid Path-State Semantics and Controlled Deployment Protocol Freeze")
    print("=" * 126)
    print("\n".join(PROHIBITIONS), flush=True)

    g = Gates()

    print("\nV16E-9-R1 CERTIFIED ADAPTER AUTHORITY")
    bind(g, "E9R1_runner", project / E9R1_RUNNER[0], E9R1_RUNNER[1])
    for key, (name, expected) in E9R1.items():
        bind(g, "E9R1_" + key, drive / E9R1_REL / name, expected)

    e9_summary = read_json(drive / E9R1_REL / E9R1["summary"][0])
    e9_audit = read_json(drive / E9R1_REL / E9R1["audit"][0])
    g.check("E9R1_status_PASS", e9_summary.get("status") == "PASS")
    g.check("E9R1_Hybrid10_1000_1000_0", [e9_summary.get("Hybrid10_identical_state_profiles"), e9_summary.get("Hybrid10_learned_accept_count"), e9_summary.get("Hybrid10_exact_fallback_count")] == [1000, 1000, 0])
    g.check("E9R1_Hybrid12_1000_970_30", [e9_summary.get("Hybrid12_identical_state_profiles"), e9_summary.get("Hybrid12_learned_accept_count"), e9_summary.get("Hybrid12_exact_fallback_count")] == [1000, 970, 30])
    g.check("E9R1_zero_unsafe_accept", e9_summary.get("zero_unsafe_accepted_proposals") is True)
    g.check("E9R1_exact_R2_fallback_certified", e9_summary.get("exact_R2_fallback_certified") is True)
    g.check("E9R1_tests_OOD_closed", e9_summary.get("internal_test_reopened") is False and e9_summary.get("OOD_opened") is False)
    g.check("E9R1_SGSim_not_yet_authorized", e9_summary.get("SGSim_deployment_authorized") is False)
    g.check("E9R1_audit_certified", e9_audit.get("reconciled_identical_state_certified") is True)

    print("\nFROZEN SCREEN / ROUTING / FEATURE AUTHORITY")
    for key, (name, expected) in E8R1.items():
        bind(g, "E8R1_" + key, drive / E8R1_REL / name, expected)
    bind(g, "E7_routing", drive / E7_REL / E7_ROUTING[0], E7_ROUTING[1])
    bind(g, "E3_protocol", drive / E3_REL / E3_PROTOCOL[0], E3_PROTOCOL[1])

    e3 = read_json(drive / E3_REL / E3_PROTOCOL[0])
    g.check("Hybrid10_features_exact", e3["experiments"]["Hybrid10"]["features"] == FEATURES10)
    g.check("Hybrid12_features_exact", e3["experiments"]["Hybrid12"]["features"] == FEATURES12)
    g.check("Hybrid10_fixed_endpoints_exact", e3["experiments"]["Hybrid10"]["fixed_endpoints"] == {"krw_max": 0.8, "kro_max": 0.8})
    g.check("E3_parameter_bounds_exact", e3["dataset_design"]["bounds"] == EXPECTED_BOUNDS)
    g.check("E3_preBT_scope_exact", e3["scope"]["time_domain"] == "positive pre-breakthrough local clocks only; 0 < xD_star < 1")
    g.check("E3_DP_role_preserves_3D_authority", "SGSim/pressure/Darcy/Pollock retain 3-D authority" in e3["scope"]["DP_role"])

    print("\nPAD-STREAM / SGSIM LINEAGE CONTEXT")
    bind(g, "V16C1_source", project / V16C1_SOURCE[0], V16C1_SOURCE[1])
    c1_text = (project / V16C1_SOURCE[0]).read_text(encoding="utf-8", errors="ignore")
    g.check("Pollock_authoritative_streamline_coordinate_present", "AUTHORITATIVE_STREAMLINE_TRANSPORT_COORDINATE" in c1_text)
    g.check("FMM_ADV_do_not_replace_Pollock", "neither may replace Pollock TOF" in c1_text or "neither may replace Pollock" in c1_text)

    source_identities = {}
    for name in SGSIM_CONTEXT_SOURCES:
        p = project / name
        g.check("source_" + name.replace(".", "_") + "_exists", p.is_file(), str(p))
        source_identities[name] = {"sha256": sha(p), "bytes": p.stat().st_size}

    sg5_text = (project / SGSIM_CONTEXT_SOURCES[1]).read_text(encoding="utf-8", errors="ignore").lower()
    sg6_text = (project / SGSIM_CONTEXT_SOURCES[2]).read_text(encoding="utf-8", errors="ignore").lower()
    sg7a_text = (project / SGSIM_CONTEXT_SOURCES[3]).read_text(encoding="utf-8", errors="ignore").lower()
    g.check("SG5_Pollock_semantics_present", "pollock" in sg5_text)
    g.check("SG6_TOF_semantics_present", "tof" in sg6_text and "transport" in sg6_text)
    g.check("SG7A_exact_transport_fallback_lineage_present", "transport" in sg7a_text and ("physics" in sg7a_text or "exact" in sg7a_text))

    print("\nV16E-10 PATH-STATE SEMANTICS CONTRACT")
    path_state = {
        "schema_version": 1,
        "milestone": MILESTONE,
        "status": SUCCESS,
        "scope": "first controlled post-V16E9-R1 use of accepted Hybrid transport on the frozen SGSim dissertation base",
        "coordinate_authority": {
            "trajectory": "existing exact 3-D Pollock path",
            "transport_coordinate": "existing Pollock TOF tau(s)",
            "terminal_TOF": "tau_end from frozen Pollock/SG6 lineage",
            "streamline_flow_weight": "existing conservative Pollock seed/path weight",
            "rule": "permeability heterogeneity is already represented upstream through pressure, Darcy flux, Pollock geometry, TOF and path weight; do not add DP kh reallocation",
        },
        "neural_constitutive_state": {
            "Hybrid10_pathwise_constants": ["no", "nw", "swc", "sor", "mu_w", "mu_o", "phi"],
            "Hybrid12_pathwise_constants": ["no", "nw", "swc", "sor", "mu_w", "mu_o", "phi", "krw_max", "kro_max"],
            "dynamic_derived_inputs": ["tD", "xD_star", "Sw_star"],
            "forbidden_neural_channels": ["absolute permeability k", "layer thickness h", "DP", "Lorenz", "layer ID", "streamline ID", "partition ID"],
            "pathwise_constant_rule": "each required constitutive quantity must be explicitly sourced and exactly constant over all Pollock cells visited by that streamline; no average, harmonic mean, PV mean, TOF mean, interpolation or fitted effective value is permitted",
            "missing_or_varying_rule": "if any required constitutive quantity is missing or varies along a path, the current Hybrid10/12 checkpoints are ineligible on that path",
        },
        "cell_property_binding": {
            "authority": "exact Pollock segment/cell provenance from the frozen SG5 path lineage",
            "resampled_node_rule": "assign cell-local metadata from exact segment membership; at a cell crossing use the downstream/right-continuous cell for tau>0 and the injector cell at tau=0",
            "prohibited": "do not infer constitutive state by nearest-neighbor or rounded XYZ lookup if exact segment/cell provenance cannot be recovered",
            "failure_policy": "block learned deployment for that path until exact cell-membership provenance is available",
        },
        "permeability_semantics": {
            "may_vary_along_path": True,
            "neural_input": False,
            "role": "upstream exact flow / TOF / streamline-weight authority only",
            "no_double_counting": True,
        },
        "Hybrid10_route": {
            "requirements": [
                "all Hybrid10 constitutive inputs explicit and pathwise constant",
                "all constitutive inputs inside E3-R1 frozen bounds",
                "krw_max and kro_max explicitly guaranteed to equal 0.8 and 0.8",
                "0.05 <= xD_star <= 0.95",
                "pre-breakthrough classical incompressible BL scope",
            ],
            "model_role": "screened learned proposal",
        },
        "Hybrid12_route": {
            "requirements": [
                "all Hybrid12 constitutive inputs explicit and pathwise constant",
                "krw_max and kro_max explicit and inside E3-R1 Hybrid12 bounds",
                "endpoint pair is not routed to Hybrid10 fixed-0.8 branch",
                "0.05 <= xD_star <= 0.95",
                "pre-breakthrough classical incompressible BL scope",
            ],
            "model_role": "screened learned proposal",
        },
        "Pollock_to_fan_mapping": {
            "tD": "physical_time / tau_end",
            "shock_state": "Sw_star and fprime(Sw_star) from exact R2 Corey/Welge physics using the selected pathwise-constant constitutive state",
            "tau_star": "physical_time * fprime(Sw_star)",
            "xD_star": "tau_star / tau_end = tD * fprime(Sw_star)",
            "fan_coordinate": "eta = tau / tau_star only on 0 <= tau <= tau_star",
            "downstream_state": "Swc for tau > tau_star",
            "blind_full_path_xi_substitution": False,
        },
        "fallback_hierarchy": {
            "proposal_rejected_but_constitutive_state_pathwise_constant": "exact R2 BL fan on the same Pollock TOF path",
            "constitutive_state_varies_along_path": "heterogeneous/full-physics TOF transport authority (V15SG7A lineage or a separately frozen successor); do NOT homogenize and do NOT call R2 homogeneous fallback",
            "fallback_authority_missing": "no learned deployment for that path",
        },
        "screening": {
            "source": "unchanged V16E-8-R1 reconciled learned-proposal screen",
            "unsafe_learned_proposal_accepted_required": 0,
            "nonzero_exact_fallback_allowed": True,
        },
        "physics_scope_boundary": {
            "authorized": "classical incompressible immiscible pre-breakthrough BL fan in Pollock TOF space",
            "not_claimed": ["post-breakthrough Hybrid transport", "compressible equivalence", "capillary equivalence", "full-physics equivalence"],
        },
    }

    deployment = {
        "schema_version": 1,
        "milestone": MILESTONE,
        "status": SUCCESS,
        "first_controlled_SGSim_reference": {
            "grid_shape_expected": [15, 50, 50],
            "cell_dimensions_ft_expected": [20.0, 20.0, 4.0],
            "streamline_count_expected": 1078,
            "common_transport_nodes_expected": 201,
            "physical_time_days": [100.0],
            "reason": "use the frozen Version-15 7x7 / 1078-streamline 100-day reference first; later times and alternate seed densities remain separate future validations",
            "must_reverify_against_artifacts_before_inference": True,
        },
        "E11_preflight_order": [
            "bind exact V16E-9-R1 / E10 authority",
            "load existing frozen SG1/SG5/SG6 artifacts without recomputation",
            "verify 50x50x15 grid, 1078 completed producer-captured paths, 201 TOF nodes and positive conservative path weights",
            "recover exact Pollock cell/segment membership for every resampled node",
            "sample constitutive metadata by exact cell membership; never by averaging or nearest-node geometry",
            "classify every path at 100 days into Hybrid10, Hybrid12, exact-R2 fallback, heterogeneous/full-physics fallback, or blocked-unresolved",
            "only after classification may accepted checkpoints be loaded for eligible Hybrid10/12 paths",
            "screen every learned proposal under V16E-8-R1; rejected proposal goes to the appropriate exact fallback",
            "require zero unsafe accepted learned proposals",
        ],
        "pilot_outputs": {
            "streamline_level_only": True,
            "grid_mapback_in_E11": False,
            "producer_aggregation_allowed": "diagnostic only from existing conservative path weights after accepted/fallback streamline states",
            "new_grid_saturation_field": False,
        },
        "authorization_on_E10_pass": {
            "E11_100_day_path_eligibility_audit": True,
            "E11_controlled_streamline_inference_after_preflight": True,
            "new_pressure_solve": False,
            "new_Darcy_flux": False,
            "new_Pollock_trace": False,
            "new_TOF_generation": False,
            "grid_mapback": False,
            "SGSim_property_modification": False,
            "checkpoint_or_routing_change": False,
            "internal_test_or_OOD_reopen": False,
        },
        "stop_conditions": [
            "frozen SGSim identity mismatch",
            "streamline/TOF count or shape mismatch",
            "exact Pollock cell-membership provenance unavailable",
            "required constitutive metadata missing or path-varying with no heterogeneous exact fallback",
            "all paths ineligible for both learned branches",
            "any unsafe learned proposal would be accepted",
        ],
        "next_milestone": NEXT_PASS,
    }

    # Self-consistency gates on the prospective freeze itself.
    g.check("pathwise_averaging_prohibited", "no average" in path_state["neural_constitutive_state"]["pathwise_constant_rule"])
    g.check("permeability_not_neural_and_may_vary", path_state["permeability_semantics"]["may_vary_along_path"] is True and path_state["permeability_semantics"]["neural_input"] is False)
    g.check("Hybrid10_fixed_endpoint_route", "0.8 and 0.8" in path_state["Hybrid10_route"]["requirements"][2])
    g.check("Hybrid12_explicit_endpoint_route", "explicit" in path_state["Hybrid12_route"]["requirements"][1])
    g.check("preBT_clock_fraction_frozen_005_095", "0.05 <= xD_star <= 0.95" in path_state["Hybrid10_route"]["requirements"] and "0.05 <= xD_star <= 0.95" in path_state["Hybrid12_route"]["requirements"])
    g.check("heterogeneous_constitutive_path_not_homogenized", "do NOT homogenize" in path_state["fallback_hierarchy"]["constitutive_state_varies_along_path"])
    g.check("zero_unsafe_accept_required", path_state["screening"]["unsafe_learned_proposal_accepted_required"] == 0)
    g.check("first_pilot_100d_only", deployment["first_controlled_SGSim_reference"]["physical_time_days"] == [100.0])
    g.check("first_pilot_1078_streamlines", deployment["first_controlled_SGSim_reference"]["streamline_count_expected"] == 1078)
    g.check("first_pilot_201_nodes", deployment["first_controlled_SGSim_reference"]["common_transport_nodes_expected"] == 201)
    g.check("E11_no_grid_mapback", deployment["authorization_on_E10_pass"]["grid_mapback"] is False)
    g.check("E11_no_pressure_Pollock_TOF_recompute", not any(deployment["authorization_on_E10_pass"][k] for k in ["new_pressure_solve", "new_Darcy_flux", "new_Pollock_trace", "new_TOF_generation"]))
    g.check("tests_OOD_remain_closed", deployment["authorization_on_E10_pass"]["internal_test_or_OOD_reopen"] is False)

    results = {
        "milestone": MILESTONE,
        "status": SUCCESS,
        "parent_E9R1_audit_sha256": E9R1["audit"][1],
        "parent_E9R1_summary_sha256": E9R1["summary"][1],
        "repository_context_source_identities": source_identities,
        "gates": g.items,
        "training_performed": False,
        "model_inference_performed": False,
        "checkpoint_loaded": False,
        "SGSim_numerical_artifact_loaded": False,
        "SGSim_deployed": False,
        "pressure_Darcy_Pollock_TOF_recomputed": False,
        "grid_mapback_performed": False,
        "checkpoint_or_routing_changed": False,
        "internal_test_reopened": False,
        "OOD_opened": False,
        "E11_controlled_streamline_pilot_authorized": True,
        "E11_grid_mapback_authorized": False,
        "next_milestone": NEXT_PASS,
    }

    path_bytes = encoded(path_state)
    deploy_bytes = encoded(deployment)
    results["path_state_contract_sha256"] = digest(path_bytes)
    results["controlled_deployment_protocol_sha256"] = digest(deploy_bytes)
    results_bytes = encoded(results)

    summary = {
        "milestone": MILESTONE,
        "status": "PASS",
        "path_state_semantics_frozen": True,
        "permeability_variation_handled_upstream_by_exact_flow_TOF": True,
        "constitutive_path_averaging_authorized": False,
        "Hybrid10_fixed_endpoint_route": True,
        "Hybrid12_explicit_variable_endpoint_route": True,
        "path_varying_constitutive_state_uses_homogeneous_R2_fallback": False,
        "unsafe_learned_proposal_acceptance_allowed": False,
        "first_controlled_time_days": 100.0,
        "first_controlled_streamline_count_expected": 1078,
        "training_or_inference_performed": False,
        "SGSim_deployed": False,
        "grid_mapback_authorized": False,
        "internal_test_reopened": False,
        "OOD_opened": False,
        "next_milestone": NEXT_PASS,
    }
    summary_bytes = encoded(summary)

    handoff = f"""# PAD-Stream V16E-10 — SGSim Hybrid Path-State Protocol Freeze PASS

V16E-9-R1 certified the Hybrid adapter on homogeneous/local states. V16E-10 now
freezes the only legal bridge to the heterogeneous SGSim dissertation base.

Key rule: spatial permeability may vary along a Pollock path because permeability
already acts through the exact pressure / Darcy / Pollock / TOF / flow-weight
chain and is not a neural conditioning channel. By contrast, every constitutive
quantity that IS a Hybrid input (phi, Swc/Sor, Corey exponents, viscosities and,
for Hybrid12, relative-permeability endpoints) must be explicit and pathwise
constant. E10 forbids averaging those quantities into an invented effective
Hybrid state.

Hybrid10 is available only for an explicit 0.8/0.8 endpoint state. Hybrid12 is
available for explicit pathwise-constant endpoints inside the frozen E3-R1
bounds. A path-varying constitutive state is not sent to homogeneous R2 by
averaging; it requires the heterogeneous/full-physics TOF fallback lineage.

The first controlled pilot is frozen to the existing Version-15 SGSim reference:
50x50x15, 1078 producer-captured Pollock streamlines, 201 TOF nodes, and 100 days.
E11 must reverify those artifact identities before inference. It may perform
streamline-level screened Hybrid inference only after path eligibility is known.
No pressure/flux/Pollock/TOF recomputation and no grid map-back are authorized.

Path-state contract SHA: {digest(path_bytes)}
Deployment protocol SHA: {digest(deploy_bytes)}
Results SHA: {digest(results_bytes)}
Summary SHA: {digest(summary_bytes)}
NEXT: {NEXT_PASS}
""".encode("utf-8")

    payloads = {
        "V16E10_SGSim_Hybrid_Path_State_Semantics.json": path_bytes,
        "V16E10_Controlled_Deployment_Protocol.json": deploy_bytes,
        "V16E10_Path_State_Protocol_Freeze_Results.json": results_bytes,
        "PAD_Stream_V16E10_Summary.json": summary_bytes,
        "V16E10_Handoff.md": handoff,
    }
    publish(out, payloads)

    print("\n" + "=" * 126)
    print("V16E-10 RESULT: PASS")
    print("=" * 126)
    print(f"{'Path-varying permeability allowed upstream':55}: YES")
    print(f"{'Pathwise constitutive averaging allowed':55}: NO")
    print(f"{'Hybrid10 / Hybrid12 routing':55}: FIXED 0.8/0.8 / EXPLICIT CONSTANT ENDPOINTS")
    print(f"{'Path-varying constitutive state':55}: HETEROGENEOUS EXACT FALLBACK / NO HOMOGENIZATION")
    print(f"{'First controlled SGSim pilot':55}: 100 d / 1078 streamlines / 201 nodes")
    print(f"{'Training / inference performed':55}: NO / NO")
    print(f"{'Pressure / Pollock / TOF recomputed':55}: NO / NO / NO")
    print(f"{'Grid map-back authorized':55}: NO")
    print(f"{'Internal test / OOD reopened':55}: NO / NO")
    for name, data in payloads.items():
        print(f"{name} SHA: {digest(data)}")
    print("Output:", out)
    print("NEXT:", NEXT_PASS)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parent)
    ap.add_argument("--drive-root", type=Path, default=Path("/content/drive/MyDrive/PAD_Stream_Compute"))
    ap.add_argument("--output-dir", type=Path)
    args = ap.parse_args(argv)
    try:
        project = args.project_root.resolve()
        drive = args.drive_root.resolve()
        out = (args.output_dir or drive / OUT_REL).resolve()
        return run(project, drive, out)
    except (GateError, OSError, ValueError, KeyError, TypeError, AssertionError, json.JSONDecodeError) as exc:
        print("\n[FAIL] V16E-10 did not close:", exc, file=sys.stderr, flush=True)
        print("No SGSim inference, map-back, checkpoint/routing change, test/OOD access, or deployment authority was published.", file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":
    sys.exit(main())
